"""RTK (Rust Token Killer) integration for Agent Guidance MCP.

Detects the rtk binary and provides subprocess wrappers for content filtering.
Falls back gracefully when rtk is not installed.
"""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("agent-guidance-mcp.rtk")

_RTK_PATH: str | None = None
_RTK_CHECKED: bool = False

# Known install locations in priority order
_KNOWN_PATHS = [
    "rtk",                              # $PATH
    shutil.which("rtk") or "",          # explicit PATH lookup
    "~/.local/bin/rtk",
    "~/.cargo/bin/rtk",
    "/usr/local/bin/rtk",
]


def _find_rtk() -> str | None:
    global _RTK_PATH, _RTK_CHECKED
    if _RTK_CHECKED:
        return _RTK_PATH
    _RTK_CHECKED = True
    for candidate in _KNOWN_PATHS:
        path = Path(candidate).expanduser()
        if path.is_file() and _test_rtk(str(path)):
            _RTK_PATH = str(path)
            logger.info("RTK found at %s", _RTK_PATH)
            return _RTK_PATH
    logger.debug("RTK not found — will use Python fallback")
    return None


def _test_rtk(path: str) -> bool:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and "rtk" in result.stdout.lower()
    except Exception:
        return False


def is_available() -> bool:
    return _find_rtk() is not None


def version() -> str | None:
    path = _find_rtk()
    if not path:
        return None
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def _run_rtk(args: list[str], stdin_text: str | None = None) -> dict[str, object]:
    """Run rtk with given args. Returns {'ok': True, 'output': str} or
    {'ok': False, 'error': str, 'fallback': 'python'}."""
    path = _find_rtk()
    if not path:
        return {"ok": False, "error": "rtk not installed", "fallback": "python"}
    try:
        result = subprocess.run(
            [path, *args],
            input=stdin_text,
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return {"ok": True, "output": result.stdout, "backend": "rtk"}
        return {"ok": False, "error": result.stderr[:200], "fallback": "python", "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "rtk subprocess timed out", "fallback": "python"}
    except (FileNotFoundError, OSError) as exc:
        return {"ok": False, "error": str(exc), "fallback": "python"}


# ── Structured wrappers ──────────────────────────────────────────────────────


def filter_read(path: str, level: str = "minimal", max_lines: int | None = None) -> str | None:
    """Run `rtk read <path> --level <level>`. Returns filtered content or None."""
    args = ["read", path, "--level", level]
    if max_lines is not None:
        args.extend(["--max-lines", str(max_lines)])
    result = _run_rtk(args)
    return result["output"] if result.get("ok") else None


def filter_grep(pattern: str, directory: str, limit: int = 50) -> str | None:
    result = _run_rtk(["grep", pattern, directory, "--max-results", str(limit)])
    return result["output"] if result.get("ok") else None


def filter_diff(file_a: str, file_b: str) -> str | None:
    result = _run_rtk(["diff", file_a, file_b])
    return result["output"] if result.get("ok") else None


def filter_ls(directory: str) -> str | None:
    result = _run_rtk(["ls", directory])
    return result["output"] if result.get("ok") else None


def filter_find(pattern: str, directory: str, max_results: int = 50) -> str | None:
    result = _run_rtk(["find", pattern, directory, "--max-results", str(max_results)])
    return result["output"] if result.get("ok") else None


def filter_curl(url: str, timeout: int = 30) -> str | None:
    result = _run_rtk(["proxy", "curl", "-sL", "--max-time", str(timeout), url])
    return result["output"] if result.get("ok") else None


def filter_stdin(text: str, level: str = "minimal") -> str | None:
    result = _run_rtk(["read", "--level", level], stdin_text=text)
    return result["output"] if result.get("ok") else None


def filter_text(text: str, language: str = "unknown") -> str | None:
    result = _run_rtk(["read", "--level", "minimal"], stdin_text=text)
    return result["output"] if result.get("ok") else None
