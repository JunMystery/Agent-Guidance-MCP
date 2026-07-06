"""Session continuity and state recovery manager for Agent Guidance MCP."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

SESSION_DIR_NAME = ".agent-context"
SESSION_FILE_NAME = "session.json"

def get_session_file(project_path: str) -> Path:
    return Path(project_path) / SESSION_DIR_NAME / SESSION_FILE_NAME

def save_session(
    project_path: str,
    task: str,
    checklist: List[Dict[str, Any]],
    current_step_index: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Save the active task session state to allow recovery/continuation."""
    session_dir = Path(project_path) / SESSION_DIR_NAME
    session_dir.mkdir(parents=True, exist_ok=True)
    
    session_data = {
        "task": task,
        "checklist": checklist,
        "current_step_index": current_step_index,
        "metadata": metadata or {},
    }
    
    # Write atomically via tempfile + rename to prevent corruption on crash
    session_file = session_dir / SESSION_FILE_NAME
    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp",
            dir=str(session_dir), delete=False,
        )
        try:
            json.dump(session_data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        finally:
            tmp.close()
        os.replace(tmp.name, str(session_file))
    except OSError as e:
        return {"success": False, "error": f"Failed to save session: {e}"}
    return session_data

def load_session(project_path: str) -> Optional[Dict[str, Any]]:
    """Load the persisted task session state if it exists."""
    session_file = get_session_file(project_path)
    if not session_file.exists():
        return None
        
    try:
        content = session_file.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict) and "task" in data:
            return data
    except Exception:
        pass
    return None

def clear_session(project_path: str) -> bool:
    """Clear/delete the persisted session file."""
    session_file = get_session_file(project_path)
    if session_file.exists():
        try:
            session_file.unlink()
            return True
        except Exception:
            return False
    return False
