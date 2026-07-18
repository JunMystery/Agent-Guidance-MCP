"""Shared constants and utilities for dashboard and embed daemon.

Pure stdlib — safe to import from anywhere.
"""
from __future__ import annotations

import importlib.resources
from pathlib import Path

DAEMON_DIR = Path.home() / ".agent-guidance"
DAEMON_PORT_FILE = DAEMON_DIR / "daemon.json"
DASHBOARD_PORT_FILE = DAEMON_DIR / "dashboard.json"
DASHBOARD_DIR = DAEMON_DIR / "dashboard"


def read_dashboard_asset(name: str) -> str:
    """Read a dashboard static asset from package resources."""
    try:
        return importlib.resources.files("agent_guidance_mcp").joinpath("dashboard_src", name).read_text(encoding="utf-8")
    except (AttributeError, ImportError, TypeError, OSError, FileNotFoundError):
        dev_path = Path(__file__).resolve().parent / "dashboard_src" / name
        if dev_path.is_file():
            return dev_path.read_text(encoding="utf-8")
        raise
    except (AttributeError, ImportError, TypeError, OSError):
        # Fallback for older python
        try:
            return importlib.resources.read_text("agent_guidance_mcp.dashboard_src", name)
        except Exception:
            # Development path fallback
            dev_path = Path(__file__).resolve().parent / "dashboard_src" / name
            if dev_path.is_file():
                return dev_path.read_text(encoding="utf-8")
            raise


def write_default_dashboard(path: Path | None) -> None:
    """Write all static dashboard files to ~/.agent-guidance/dashboard/ with content-hash cache busting."""
    import hashlib
    import shutil

    target_dir = path.parent if path else DASHBOARD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    css_content = read_dashboard_asset("dashboard.css")
    css_hash = hashlib.sha256(css_content.encode("utf-8")).hexdigest()[:12]
    js_hash = hashlib.sha256(read_dashboard_asset("js/main.js").encode("utf-8")).hexdigest()[:12]

    index_template = read_dashboard_asset("index.html")
    index_html = index_template.replace("{{css_hash}}", css_hash).replace("{{js_hash}}", js_hash)

    index_path = path if path else DASHBOARD_DIR / "index.html"
    try:
        index_path.write_text(index_html, encoding="utf-8")
    except Exception:
        pass

    try:
        (target_dir / "dashboard.css").write_text(css_content, encoding="utf-8")
    except Exception:
        pass

    js_src = _dashboard_src_dir() / "js"
    js_dst = target_dir / "js"
    try:
        if js_dst.exists():
            shutil.rmtree(js_dst)
        shutil.copytree(js_src, js_dst)
    except Exception:
        pass


def _dashboard_src_dir() -> Path:
    """Resolve the dashboard_src directory (package resource or dev path)."""
    dev_path = Path(__file__).resolve().parent / "dashboard_src"
    if dev_path.is_dir():
        return dev_path
    for parent in Path(__file__).resolve().parents:
        cand = parent / "agent_guidance_mcp" / "dashboard_src"
        if cand.is_dir():
            return cand
    return dev_path


def _pid_is_our_daemon(pid: int, port: int | None = None) -> bool:
    """Best-effort check that ``pid`` is the embedding daemon we spawned.

    A manifest can hold a recycled PID after a crash, so never signal a PID
    based solely on the manifest. We confirm identity via:
      1. psutil process name / cmdline (if available), and/or
      2. an HTTP /health probe on the recorded port echoing the same pid.

    Returns False if we cannot prove identity — callers must then NOT kill.
    """
    import os

    # Cheap, reliable cross-platform check: the daemon answers /health with its
    # own pid. If it responds and the pid matches, it's ours.
    if port is not None:
        try:
            import httpx

            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
            if r.is_success:
                body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                live_pid = body.get("pid")
                if isinstance(live_pid, int):
                    return live_pid == pid
        except Exception:
            pass

    try:
        import psutil
    except ImportError:
        # No psutil: cannot verify identity safely, so refuse to kill.
        return False
    try:
        p = psutil.Process(pid)
        cmdline = " ".join(p.cmdline()).lower()
        name = (p.name() or "").lower()
        return "embed_daemon" in cmdline or "agent_guidance_mcp.embed_daemon" in cmdline or "agent-guidance-mcp" in name
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
        return False


def _pid_alive(pid: int) -> bool | None:
    """Return True/False if a PID is alive, or None if indeterminate.

    On Windows ``os.kill(pid, 0)`` raises OSError for permission mismatches even
    when the process is alive, so we prefer psutil and only fall back to a strict
    "process does not exist" interpretation.
    """
    try:
        import psutil

        try:
            p = psutil.Process(pid)
            return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            return False
    except ImportError:
        import os

        try:
            os.kill(pid, 0)
            return True
        except OSError:
            # On POSIX this means the process is gone; on Windows it may be a
            # permission error for a live process — report indeterminate.
            import sys

            if sys.platform == "win32":
                return None
            return False


def kill_existing_daemon() -> None:
    """Read daemon.json and terminate the running daemon to free the port.

    Safety: a stale manifest can reference a PID that has since been reused by
    an unrelated process. We only signal the PID after confirming via
    :func:`_pid_is_our_daemon` that it is actually our embedding daemon; this
    prevents killing innocent processes (e.g. a sibling MCP server) on Windows.
    """
    import json
    import os
    import signal
    import time
    import logging

    if not DAEMON_PORT_FILE.is_file():
        return
    try:
        manifest = json.loads(DAEMON_PORT_FILE.read_text(encoding="utf-8"))
        pid = manifest.get("pid")
        port = manifest.get("port")
        if pid and _pid_is_our_daemon(pid, port):
            try:
                logger = logging.getLogger("agent-guidance-mcp.daemon")
                logger.info(f"Terminating active daemon/dashboard process {pid}")
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.1)
                    alive = _pid_alive(pid)
                    if alive is False:
                        break
                else:
                    os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    except Exception:
        pass
    try:
        DAEMON_PORT_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def kill_existing_dashboard() -> None:
    """Terminate a running *dashboard* server (mode == "dashboard") only.

    The dashboard writes its own ``dashboard.json`` manifest so it never
    collides with the shared embedding daemon's ``daemon.json``. We only ever
    kill a process recorded in ``dashboard.json`` *and* confirmed to be our
    dashboard (identity via :func:`_pid_is_our_daemon`), so we never touch the
    shared embed daemon or any unrelated process.
    """
    import json
    import os
    import signal
    import time
    import logging

    if not DASHBOARD_PORT_FILE.is_file():
        return
    try:
        manifest = json.loads(DASHBOARD_PORT_FILE.read_text(encoding="utf-8"))
        if manifest.get("mode") != "dashboard":
            return
        pid = manifest.get("pid")
        if pid and _pid_is_our_daemon(pid):
            try:
                logger = logging.getLogger("agent-guidance-mcp.dashboard")
                logger.info(f"Terminating existing dashboard process {pid}")
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.1)
                    alive = _pid_alive(pid)
                    if alive is False:
                        break
                else:
                    os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    except Exception:
        pass
    try:
        DASHBOARD_PORT_FILE.unlink(missing_ok=True)
    except OSError:
        pass



    """Trigger the native file explorer directory selection dialog depending on the OS."""
    import sys
    import os
    import subprocess
    import shutil

    if sys.platform == "darwin":
        cmd = ["osascript", "-e", 'POSIX path of (choose folder with prompt "Select Project Folder")']
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            if out and os.path.isdir(out):
                return out
        except Exception:
            pass

    elif sys.platform == "win32":
        ps_code = (
            "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;"
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog;"
            "$f.Description = 'Select Project Folder';"
            "if($f.ShowDialog() -eq 'OK') { $f.SelectedPath }"
        )
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_code]
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            if out and os.path.isdir(out):
                return out
        except Exception:
            pass

    else:
        if shutil.which("zenity"):
            cmd = ["zenity", "--file-selection", "--directory", "--title=Select Project Folder"]
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                if out and os.path.isdir(out):
                    return out
            except Exception:
                pass
        elif shutil.which("kdialog"):
            cmd = ["kdialog", "--getexistingdirectory", ".", "--title", "Select Project Folder"]
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                if out and os.path.isdir(out):
                    return out
            except Exception:
                pass

    return None
