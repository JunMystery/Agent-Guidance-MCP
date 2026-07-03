"""Background watcher for incremental CodeGraph workspace re-indexing."""

import time
import logging
import threading
from pathlib import Path
from typing import Dict

from .database import CodeGraphDatabase
from .indexer import CodeGraphIndexer
from .project_scan import iter_project_files

logger = logging.getLogger("agent-guidance-mcp.watcher")

class CodeGraphWatcher:
    """Polls workspace files for modifications and incrementally updates the CodeGraph index."""

    def __init__(self, root: Path, db: CodeGraphDatabase, interval_seconds: float = 5.0):
        self.root = root
        self.db = db
        self.interval = interval_seconds
        self.indexer = CodeGraphIndexer(root, db)
        self._stop_event = threading.Event()
        self._thread = None
        self._file_mtimes: Dict[str, int] = {}
        self._load_initial_state()

    def _load_initial_state(self) -> None:
        """Load currently indexed files and mtimes from the database."""
        try:
            cur = self.db.conn.cursor()
            cur.execute("SELECT path, modified_at FROM files;")
            for row in cur.fetchall():
                self._file_mtimes[row["path"]] = row["modified_at"]
        except Exception as e:
            logger.error(f"Failed to load initial watcher state: {e}")

    def start(self) -> None:
        """Start the background polling thread."""
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="CodeGraphWatcher")
        self._thread.start()
        logger.info(f"Started CodeGraph file watcher with interval={self.interval}s")

    def stop(self) -> None:
        """Stop the background polling thread."""
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=2)
        self._thread = None
        logger.info("Stopped CodeGraph file watcher")

    def _run_loop(self) -> None:
        """Loop running periodically to check for updates."""
        while not self._stop_event.is_set():
            try:
                self.poll()
            except Exception as e:
                logger.error(f"Error during CodeGraph watcher poll: {e}")
            self._stop_event.wait(self.interval)

    def poll(self) -> None:
        """Scan workspace and update modified/added/deleted files."""
        # 1. Gather all current files on disk
        try:
            disk_files = list(iter_project_files(self.root))
        except Exception as e:
            logger.error(f"Failed to scan workspace files: {e}")
            return

        current_disk_paths = set()
        updated_files = []
        
        # 2. Check for modifications and additions
        for path in disk_files:
            try:
                stat = path.stat()
                mtime = int(stat.st_mtime * 1000)
                size = stat.st_size
            except Exception:
                continue

            rel_path = str(path.relative_to(self.root)).replace("\\", "/")
            current_disk_paths.add(rel_path)

            stored_mtime = self._file_mtimes.get(rel_path)
            if stored_mtime is None or stored_mtime != mtime:
                # File modified or added
                updated_files.append((path, rel_path, mtime))

        # 3. Check for deletions
        deleted_paths = set(self._file_mtimes.keys()) - current_disk_paths

        changes_detected = False

        # Process deletions
        for rel_path in deleted_paths:
            try:
                self.db.delete_file(rel_path)
                self._file_mtimes.pop(rel_path, None)
                changes_detected = True
                logger.debug(f"CodeGraph watcher: removed deleted file {rel_path}")
            except Exception as e:
                logger.error(f"Failed to delete index for {rel_path}: {e}")

        # Process updates/additions
        for path, rel_path, mtime in updated_files:
            try:
                res = self.indexer.index_file(path)
                if res:
                    # Write to database
                    self.db.update_file(
                        path=res["path"],
                        content_hash=res["content_hash"],
                        size=res["size"],
                        modified_at=res["modified_at"],
                        indexed_at=int(time.time() * 1000),
                        node_count=len(res["symbols"]),
                        errors=res.get("errors")
                    )
                    if res["symbols"]:
                        self.db.insert_symbols(res["symbols"])
                    
                # Update our cache regardless (so we don't spin-poll if index fails)
                self._file_mtimes[rel_path] = mtime
                changes_detected = True
                logger.debug(f"CodeGraph watcher: indexed modified file {rel_path}")
            except Exception as e:
                logger.error(f"Failed to index modified file {rel_path}: {e}")

        # 4. Rebuild relationship edges if any changes occurred
        if changes_detected:
            try:
                self.indexer._resolve_references()
                self.db.optimize()
            except Exception as e:
                logger.error(f"Failed to resolve references or optimize DB: {e}")
