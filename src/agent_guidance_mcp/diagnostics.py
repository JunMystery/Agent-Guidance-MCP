"""System and database diagnostics helper for Agent Guidance MCP."""

import os
import sys
import time
import socket
import sqlite3
from pathlib import Path
from typing import Any

from .catalog import StandardsCatalog

def run_diagnostics(project_root: Path, catalog: StandardsCatalog) -> dict[str, Any]:
    """Perform system, tree-sitter, database, and network diagnostics."""
    diagnostics = {}

    # 1. Environment & System Info
    diagnostics["system"] = {
        "os": sys.platform,
        "python_version": sys.version,
        "pid": os.getpid(),
        "project_root": str(project_root.resolve()),
    }

    # 2. Tree-Sitter Status
    try:
        from tree_sitter_languages import get_parser
        has_tree_sitter = True
    except ImportError:
        has_tree_sitter = False

    supported_languages = {}
    if has_tree_sitter:
        languages = ["python", "javascript", "typescript", "go", "rust", "java", "csharp"]
        for lang in languages:
            try:
                parser = get_parser(lang)
                supported_languages[lang] = parser is not None
            except Exception as e:
                supported_languages[lang] = f"Error: {e}"

    diagnostics["tree_sitter"] = {
        "installed": has_tree_sitter,
        "languages": supported_languages,
    }

    # 3. CodeGraph Database Diagnostics
    db_path = project_root / ".agent-context" / "codegraph.db"
    db_info: dict[str, Any] = {
        "path": str(db_path),
        "exists": db_path.is_file(),
    }

    if db_path.is_file():
        db_info["size_bytes"] = db_path.stat().st_size
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            
            # File count
            file_count = conn.execute("SELECT COUNT(*) FROM files;").fetchone()[0]
            db_info["files_indexed"] = file_count
            
            # Symbol count
            symbol_count = conn.execute("SELECT COUNT(*) FROM symbols;").fetchone()[0]
            db_info["symbols_indexed"] = symbol_count
            
            # Call edge count
            edge_count = conn.execute("SELECT COUNT(*) FROM call_edges;").fetchone()[0]
            db_info["call_edges_indexed"] = edge_count
            
            # Oldest / Newest indexed timestamps
            timestamps = conn.execute("SELECT MIN(indexed_at), MAX(indexed_at) FROM files;").fetchone()
            if timestamps and timestamps[0] is not None:
                db_info["oldest_indexed_at_ms"] = timestamps[0]
                db_info["newest_indexed_at_ms"] = timestamps[1]
                db_info["oldest_indexed_age_sec"] = int(time.time() - (timestamps[0] / 1000.0))
            
            conn.close()
            db_info["status"] = "healthy"
        except Exception as e:
            db_info["status"] = "unhealthy"
            db_info["error"] = str(e)
    else:
        db_info["status"] = "missing"

    diagnostics["database"] = db_info

    # 4. Context7 Connectivity Check
    network_info = {}
    try:
        # Resolve host
        host = "context7.com"
        ip = socket.gethostbyname(host)
        network_info["dns_resolves"] = True
        network_info["ip_address"] = ip
        
        # Test quick TCP connection on port 443
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((host, 443))
        s.close()
        network_info["tcp_connection"] = "success"
    except Exception as e:
        network_info["dns_resolves"] = False
        network_info["error"] = str(e)

    diagnostics["context7_api"] = network_info

    # 5. Standards Catalog Stats
    try:
        manifest = catalog.manifest()
        diagnostics["catalog"] = {
            "entry_count": manifest.get("entry_count", 0),
            "categories": list(manifest.get("categories", {}).keys()),
        }
    except Exception as e:
        diagnostics["catalog"] = {"error": str(e)}

    return diagnostics
