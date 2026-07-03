"""Incremental workspace indexing engine for CodeGraph intelligence."""

import hashlib
import time
from pathlib import Path
from typing import Generator

from .database import CodeGraphDatabase
from .symbols import extract_symbols, find_references
from .project_scan import iter_project_files
from .parallel import parallel_map

class CodeGraphIndexer:
    """Indexes workspace files, extracts symbols/edges, and maintains the database."""

    def __init__(self, root: Path, db: CodeGraphDatabase):
        self.root = root
        self.db = db

    def _compute_hash(self, path: Path) -> str:
        """Compute MD5 hash of file content."""
        hasher = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def index_file(self, path: Path) -> dict | None:
        """Parse symbols from a single file and return for database insertion."""
        if not path.is_file():
            return None

        stat = path.stat()
        mtime = int(stat.st_mtime * 1000)
        size = stat.st_size
        rel = str(path.relative_to(self.root)).replace("\\", "/")
        
        # Check if file has changed
        existing = self.db.get_file(rel)
        if existing and existing["modified_at"] == mtime and existing["size"] == size:
            # File is fresh
            return None

        content_hash = self._compute_hash(path)
        if existing and existing["content_hash"] == content_hash:
            # Hash matches, just update stats
            self.db.update_file(rel, content_hash, size, mtime, int(time.time() * 1000), existing["node_count"])
            return None

        # Re-parse symbols
        try:
            extracted = extract_symbols(path, self.root)
            symbols_data = [
                {
                    "name": s.name,
                    "kind": s.kind,
                    "file_path": rel,
                    "parent": s.parent,
                    "start_line": s.line,
                    "end_line": s.end_line,
                    "signature": s.signature,
                }
                for s in extracted
            ]
            return {
                "path": rel,
                "content_hash": content_hash,
                "size": size,
                "modified_at": mtime,
                "symbols": symbols_data,
            }
        except Exception as e:
            return {
                "path": rel,
                "content_hash": content_hash,
                "size": size,
                "modified_at": mtime,
                "symbols": [],
                "errors": [str(e)],
            }

    def run(self) -> dict[str, int]:
        """Scan the project and run incremental indexing."""
        all_files = list(iter_project_files(self.root))
        
        # Parse files in parallel
        results = parallel_map(self.index_file, all_files)
        
        updates_count = 0
        symbols_count = 0
        
        # Write updates to db
        for res in results:
            if not res:
                continue
            path = res["path"]
            self.db.update_file(
                path=path,
                content_hash=res["content_hash"],
                size=res["size"],
                modified_at=res["modified_at"],
                indexed_at=int(time.time() * 1000),
                node_count=len(res["symbols"]),
                errors=res.get("errors")
            )
            if res["symbols"]:
                self.db.insert_symbols(res["symbols"])
                symbols_count += len(res["symbols"])
            updates_count += 1

        # Delete files that no longer exist
        db_files = {row["path"] for row in self.db.conn.execute("SELECT path FROM files;").fetchall()}
        disk_files = {str(p.relative_to(self.root)).replace("\\", "/") for p in all_files}
        deleted_files = db_files - disk_files
        for df in deleted_files:
            self.db.delete_file(df)
            updates_count += 1

        # Build basic relationship edges (call graphs)
        if updates_count > 0:
            self._resolve_references()
            try:
                self.db.optimize()
            except Exception:
                pass

        return {
            "scanned": len(all_files),
            "updated": updates_count,
            "deleted": len(deleted_files),
            "symbols_added": symbols_count,
        }

    def _resolve_references(self) -> None:
        """Resolve symbol call graph edges across the codebase."""
        # Clear existing edges
        with self.db.conn:
            self.db.conn.execute("DELETE FROM call_edges;")

        # Fetch all symbols
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, name, kind, file_path FROM symbols WHERE kind IN ('function', 'method');")
        all_functions = cur.fetchall()
        
        # Build reference edges
        edges = []
        for func in all_functions:
            func_id = func["id"]
            name = func["name"]
            
            # Find references to this function
            refs = find_references(self.root, name, limit=50)
            for ref in refs:
                # Find caller symbol inside the ref file containing the reference line
                ref_file = ref["file"]
                ref_line = ref["line"]
                
                caller = self.db.conn.execute(
                    "SELECT id FROM symbols WHERE file_path = ? AND start_line <= ? AND end_line >= ? AND kind IN ('function', 'method') LIMIT 1;",
                    (ref_file, ref_line, ref_line)
                ).fetchone()
                
                if caller and caller["id"] != func_id:
                    edges.append({
                        "source": caller["id"],
                        "target": func_id,
                        "line": ref_line
                    })
                    
        self.db.insert_edges(edges)
