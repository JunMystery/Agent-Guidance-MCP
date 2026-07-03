"""CodeGraph-related project context helper functions."""

from pathlib import Path
from .database import CodeGraphDatabase
from .symbols import extract_symbols, find_references, get_file_structure
from .project_scan import (
    language_hint,
    ensure_project_file_allowed,
    relative_path,
    resolve_inside_project,
    resolve_project_root,
)
from .token_config import TokenOptimizationConfig, load_config_from_env

def _get_db(root: Path) -> CodeGraphDatabase:
    """Return database connection for the resolved project root."""
    return CodeGraphDatabase(root / ".agent-context" / "codegraph.db")

def extract_project_symbols(
    project_path: str = ".",
    relative_path_value: str = "",
    config: TokenOptimizationConfig | None = None,
    tracker: object | None = None,
) -> dict[str, object]:
    """Extract symbols (classes, functions, methods) from a file."""
    if not relative_path_value:
        raise ValueError("relative_path is required.")
    root = resolve_project_root(project_path)
    path = resolve_inside_project(root, relative_path_value)
    ensure_project_file_allowed(root, path)

    # Try DB first
    db = _get_db(root)
    try:
        rel = relative_path(root, path)
        rows = db.get_symbols_in_file(rel)
        if rows:
            symbols_dicts = [dict(r) for r in rows]
            return {
                "project_root": str(root),
                "file": rel,
                "language": language_hint(path),
                "symbols": symbols_dicts,
                "total": len(symbols_dicts),
            }
    except Exception:
        pass
    finally:
        db.close()

    # Live fallback
    symbols = extract_symbols(path, root)
    return {
        "project_root": str(root),
        "file": relative_path(root, path),
        "language": language_hint(path),
        "symbols": [s.to_dict() for s in symbols],
        "total": len(symbols),
    }

def find_project_references(
    project_path: str = ".",
    symbol_name: str = "",
    limit: int = 20,
    config: TokenOptimizationConfig | None = None,
    tracker: object | None = None,
) -> dict[str, object]:
    """Find where a symbol is referenced across the codebase."""
    root = resolve_project_root(project_path)
    limit = max(1, min(limit, 100))

    matches = find_references(root, symbol_name, limit=limit)
    return {
        "project_root": str(root),
        "symbol": symbol_name,
        "matches": matches,
        "total": len(matches),
    }

def get_project_file_structure(
    project_path: str = ".",
    relative_path_value: str = "",
    config: TokenOptimizationConfig | None = None,
    tracker: object | None = None,
) -> dict[str, object]:
    """Return hierarchical structure (classes, methods, functions) of a file."""
    config = config or load_config_from_env()
    if not relative_path_value:
        raise ValueError("relative_path is required.")
    root = resolve_project_root(project_path)
    path = resolve_inside_project(root, relative_path_value)
    ensure_project_file_allowed(root, path)
    structure = get_file_structure(path, root)

    if config.enabled:
        from .response_optimizer import optimize_source_content
        raw = str(structure)
        optimized, _ = optimize_source_content(raw, "json", config=config)
        import json
        try:
            structure = json.loads(optimized)
        except (json.JSONDecodeError, TypeError):
            pass

    return structure

def get_project_callers(
    project_path: str = ".",
    symbol_id: str = "",
    config: TokenOptimizationConfig | None = None,
    tracker: object | None = None,
) -> dict[str, object]:
    """Get all callers of a given symbol ID from the database."""
    if not symbol_id:
        raise ValueError("symbol_id is required.")
    root = resolve_project_root(project_path)
    db = _get_db(root)
    try:
        callers = db.get_callers(symbol_id)
        results = [dict(c) for c in callers]
        return {
            "project_root": str(root),
            "symbol_id": symbol_id,
            "callers": results,
            "total": len(results),
        }
    finally:
        db.close()

def get_project_callees(
    project_path: str = ".",
    symbol_id: str = "",
    config: TokenOptimizationConfig | None = None,
    tracker: object | None = None,
) -> dict[str, object]:
    """Get all callees of a given symbol ID from the database."""
    if not symbol_id:
        raise ValueError("symbol_id is required.")
    root = resolve_project_root(project_path)
    db = _get_db(root)
    try:
        callees = db.get_callees(symbol_id)
        results = [dict(c) for c in callees]
        return {
            "project_root": str(root),
            "symbol_id": symbol_id,
            "callees": results,
            "total": len(results),
        }
    finally:
        db.close()
