"""SQLite database connection and schema management for CodeGraph-like indexing."""

import sqlite3
from pathlib import Path
import json

class CodeGraphDatabase:
    """Manages SQLite storage for symbols, files, and reference edges."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize tables and run migrations if needed."""
        with self.conn:
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON;")
            
            # Schema version table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_versions (
                    version INTEGER PRIMARY KEY,
                    applied_at INTEGER NOT NULL,
                    description TEXT
                );
            """)

            # Core tables
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    modified_at INTEGER NOT NULL,
                    indexed_at INTEGER NOT NULL,
                    node_count INTEGER DEFAULT 0,
                    errors TEXT
                );
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    parent TEXT,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    signature TEXT,
                    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
                );
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS call_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    FOREIGN KEY (source) REFERENCES symbols(id) ON DELETE CASCADE,
                    FOREIGN KEY (target) REFERENCES symbols(id) ON DELETE CASCADE
                );
            """)

            # Create FTS5 virtual table for symbols
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
                    name,
                    kind,
                    signature,
                    content='symbols',
                    content_rowid='rowid'
                );
            """)

            # Triggers to keep FTS5 virtual table updated
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols BEGIN
                    INSERT INTO symbols_fts(rowid, name, kind, signature)
                    VALUES (new.rowid, new.name, new.kind, new.signature);
                END;
            """)

            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols BEGIN
                    INSERT INTO symbols_fts(symbols_fts, rowid, name, kind, signature)
                    VALUES('delete', old.rowid, old.name, old.kind, old.signature);
                END;
            """)

            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols BEGIN
                    INSERT INTO symbols_fts(symbols_fts, rowid, name, kind, signature)
                    VALUES('delete', old.rowid, old.name, old.kind, old.signature);
                    INSERT INTO symbols_fts(rowid, name, kind, signature)
                    VALUES (new.rowid, new.name, new.kind, new.signature);
                END;
            """)

    def rebuild(self) -> None:
        """Clear database tables and reinitialize."""
        with self.conn:
            self.conn.execute("DROP TABLE IF EXISTS call_edges;")
            self.conn.execute("DROP TABLE IF EXISTS symbols_fts;")
            self.conn.execute("DROP TABLE IF EXISTS symbols;")
            self.conn.execute("DROP TABLE IF EXISTS files;")
            self._init_db()

    def update_file(self, path: str, content_hash: str, size: int, modified_at: int, indexed_at: int, node_count: int, errors: list[str] | None = None) -> None:
        """Upsert a file record in the db."""
        err_str = json.dumps(errors) if errors else None
        with self.conn:
            # Delete old symbols and edges for this file (cascades)
            self.conn.execute("DELETE FROM files WHERE path = ?;", (path,))
            
            # Insert file record
            self.conn.execute(
                "INSERT INTO files (path, content_hash, size, modified_at, indexed_at, node_count, errors) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (path, content_hash, size, modified_at, indexed_at, node_count, err_str)
            )

    def delete_file(self, path: str) -> None:
        """Delete a file and its symbols/edges."""
        with self.conn:
            self.conn.execute("DELETE FROM files WHERE path = ?;", (path,))

    def get_file(self, path: str) -> sqlite3.Row | None:
        """Retrieve a file record by path."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM files WHERE path = ?;", (path,))
        return cur.fetchone()

    def insert_symbols(self, symbols: list[dict]) -> None:
        """Bulk insert symbols."""
        if not symbols:
            return
        with self.conn:
            self.conn.executemany(
                "INSERT INTO symbols (id, name, kind, file_path, parent, start_line, end_line, signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                [(f"{s['file_path']}::{s['parent'] or ''}::{s['name']}", s['name'], s['kind'], s['file_path'], s['parent'], s['start_line'], s['end_line'], s['signature']) for s in symbols]
            )

    def insert_edges(self, edges: list[dict]) -> None:
        """Bulk insert call edges."""
        if not edges:
            return
        with self.conn:
            self.conn.executemany(
                "INSERT INTO call_edges (source, target, line) VALUES (?, ?, ?);",
                [(e['source'], e['target'], e['line']) for e in edges]
            )

    def search_symbols(self, query: str, limit: int = 20) -> list[sqlite3.Row]:
        """Search symbols using FTS5 virtual table."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.* FROM symbols s
            JOIN symbols_fts f ON s.rowid = f.rowid
            WHERE symbols_fts MATCH ?
            ORDER BY rank
            LIMIT ?;
        """, (query, limit))
        return cur.fetchall()

    def get_symbols_in_file(self, file_path: str) -> list[sqlite3.Row]:
        """Get all symbols inside a file."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM symbols WHERE file_path = ? ORDER BY start_line;", (file_path,))
        return cur.fetchall()

    def get_callers(self, target_symbol_id: str) -> list[sqlite3.Row]:
        """Get callers of a target symbol."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.*, e.line FROM symbols s
            JOIN call_edges e ON s.id = e.source
            WHERE e.target = ?;
        """, (target_symbol_id,))
        return cur.fetchall()

    def get_callees(self, source_symbol_id: str) -> list[sqlite3.Row]:
        """Get callees of a source symbol."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.*, e.line FROM symbols s
            JOIN call_edges e ON s.id = e.target
            WHERE e.source = ?;
        """, (source_symbol_id,))
        return cur.fetchall()

    def close(self) -> None:
        self.conn.close()
