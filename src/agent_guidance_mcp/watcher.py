"""Background watcher for incremental CodeGraph workspace re-indexing.

CPU-aware: debounced polling with configurable interval, batched reference
resolution, and env-var disable. See AGENT_WATCHER_INTERVAL and
AGENT_WATCHER_ENABLED.
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Set

from .database import CodeGraphDatabase
from .indexer import CodeGraphIndexer
from .project_scan import iter_project_files, invalidate_tree_cache

logger = logging.getLogger("agent-guidance-mcp.watcher")

# ── Env-configurable defaults ────────────────────────────────────────────────
_DEFAULT_INTERVAL = float(os.environ.get("AGENT_WATCHER_INTERVAL", "30.0"))
# After detecting changes, wait this multiple of the base interval before the
# next full scan so writes don't keep the CPU pegged.
_DEBOUNCE_MULTIPLIER = float(os.environ.get("AGENT_WATCHER_DEBOUNCE_MULTIPLIER", "2.0"))
# Only trigger full _resolve_references after at least this many changed files
# accumulate (or after a quiet period).  Keeps O(n²) graph rebuilds rare.
_REFERENCE_RESOLVE_THRESHOLD = int(os.environ.get("AGENT_WATCHER_REF_THRESHOLD", "50"))


class CodeGraphWatcher:
    """Polls workspace files for modifications and incrementally updates the
    CodeGraph index with debounce and batching."""

    def __init__(self, root: Path, db: CodeGraphDatabase, interval_seconds: float | None = None):
        self.root = root
        self.db = db
        self.interval = interval_seconds if interval_seconds is not None else _DEFAULT_INTERVAL
        self.debounce_interval = self.interval * _DEBOUNCE_MULTIPLIER
        self.indexer = CodeGraphIndexer(root, db)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._file_mtimes: Dict[str, int] = {}
        # Track files changed since the last reference resolution
        self._pending_changes: Set[str] = set()
        self._last_change_time: float = 0.0
        self._load_initial_state()
        logger.info(
            "CodeGraphWatcher init: interval=%.1fs debounce=%.1fs ref_threshold=%d",
            self.interval, self.debounce_interval, _REFERENCE_RESOLVE_THRESHOLD,
        )

    def _load_initial_state(self) -> None:
        """Load currently indexed files and mtimes from the database."""
        try:
            cur = self.db.conn.cursor()
            cur.execute("SELECT path, modified_at FROM files;")
            for row in cur.fetchall():
                self._file_mtimes[row["path"]] = row["modified_at"]
        except Exception as e:
            logger.error("Failed to load initial watcher state: %s", e)

    def start(self) -> None:
        """Start the background polling thread."""
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="CodeGraphWatcher"
        )
        self._thread.start()
        logger.info("Started CodeGraph file watcher with interval=%.1fs", self.interval)

    def stop(self) -> None:
        """Stop the background polling thread."""
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=2)
        self._thread = None
        logger.info("Stopped CodeGraph file watcher")

    # ── Polling loop with debounce ──────────────────────────────────────────

    def _run_loop(self) -> None:
        """Loop running periodically to check for updates with adaptive timing."""
        while not self._stop_event.is_set():
            try:
                self.poll()
            except Exception as e:
                logger.error("Error during CodeGraph watcher poll: %s", e)

            # Adaptive wait: longer if we just processed changes
            if self._last_change_time > 0:
                elapsed = time.time() - self._last_change_time
                if elapsed < self.debounce_interval:
                    wait = self.debounce_interval - elapsed
                else:
                    wait = self.interval
                    # Quiet period elapsed — resolve accumulated references
                    self._maybe_resolve_references()
            else:
                wait = self.interval
            self._stop_event.wait(wait)

    def _maybe_resolve_references(self) -> None:
        """Resolve references if enough changes accumulated since last time."""
        if not self._pending_changes:
            return
        if len(self._pending_changes) >= _REFERENCE_RESOLVE_THRESHOLD:
            logger.info(
                "CodeGraph watcher: %d pending changes — resolving references",
                len(self._pending_changes),
            )
            self._resolve_references_safe()
            self._pending_changes.clear()
            self._last_change_time = 0.0

    def _resolve_references_safe(self) -> None:
        """Resolve references with error handling."""
        try:
            self.indexer._resolve_references()
            self.db.optimize()
        except Exception as e:
            logger.error("Failed to resolve references or optimize DB: %s", e)

    # ── Core scan logic ─────────────────────────────────────────────────────

    def poll(self) -> None:
        """Scan workspace and update modified/added/deleted files.

        Uses os.walk (which internally uses scandir on Python ≥3.5) for
        efficient directory traversal.  Only re-indexes files whose mtime
        changed.  Reference resolution is deferred to quiet periods.
        """
        # 1. Gather all current files on disk
        try:
            disk_files = list(iter_project_files(self.root))
        except Exception as e:
            logger.error("Failed to scan workspace files: %s", e)
            return

        current_disk_paths: Set[str] = set()
        updated_files: list[tuple[Path, str, int]] = []

        # 2. Check for modifications and additions
        for path in disk_files:
            try:
                stat = path.stat()
                mtime = int(stat.st_mtime * 1000)
            except Exception:
                continue

            rel_path = str(path.relative_to(self.root)).replace("\\", "/")
            current_disk_paths.add(rel_path)

            stored_mtime = self._file_mtimes.get(rel_path)
            if stored_mtime is None or stored_mtime != mtime:
                updated_files.append((path, rel_path, mtime))

        # 3. Check for deletions
        deleted_paths = set(self._file_mtimes.keys()) - current_disk_paths

        changes_detected = bool(updated_files or deleted_paths)

        # Process deletions
        for rel_path in deleted_paths:
            try:
                self.db.delete_file(rel_path)
                self._file_mtimes.pop(rel_path, None)
                self._pending_changes.add(rel_path)
                logger.debug("CodeGraph watcher: removed deleted file %s", rel_path)
            except Exception as e:
                logger.error("Failed to delete index for %s: %s", rel_path, e)

        # Process updates/additions
        for path, rel_path, mtime in updated_files:
            try:
                res = self.indexer.index_file(path)
                if res:
                    self.db.update_file(
                        path=res["path"],
                        content_hash=res["content_hash"],
                        size=res["size"],
                        modified_at=res["modified_at"],
                        indexed_at=int(time.time() * 1000),
                        node_count=len(res["symbols"]),
                        errors=res.get("errors"),
                    )
                    if res["symbols"]:
                        self.db.insert_symbols(res["symbols"])

                # Update cache regardless (prevent spin-poll on index failure)
                self._file_mtimes[rel_path] = mtime
                self._pending_changes.add(rel_path)
                logger.debug("CodeGraph watcher: indexed modified file %s", rel_path)
            except Exception as e:
                logger.error("Failed to index modified file %s: %s", rel_path, e)

        # Track change timestamp for debounce
        if changes_detected:
            invalidate_tree_cache(self.root)
            self._last_change_time = time.time()
            logger.debug(
                "CodeGraph watcher: %d updates, %d deletions — "
                "deferring reference resolution",
                len(updated_files), len(deleted_paths),
            )

        # If the batch is small enough, resolve immediately
        if changes_detected and len(self._pending_changes) >= _REFERENCE_RESOLVE_THRESHOLD:
            logger.info(
                "CodeGraph watcher: threshold reached (%d changes) — "
                "resolving references now",
                len(self._pending_changes),
            )
            self._resolve_references_safe()
            self._pending_changes.clear()
            self._last_change_time = 0.0
