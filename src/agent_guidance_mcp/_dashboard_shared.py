"""Shared constants and utilities for dashboard and embed daemon.

Pure stdlib — safe to import from anywhere.
"""
from __future__ import annotations

import importlib.resources
from pathlib import Path

DAEMON_DIR = Path.home() / ".agent-guidance"
DAEMON_PORT_FILE = DAEMON_DIR / "daemon.json"
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


def kill_existing_daemon() -> None:
    """Read daemon.json and terminate any running daemon process to free the port."""
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
        if pid:
            try:
                os.kill(pid, 0)
                logger = logging.getLogger("agent-guidance-mcp.daemon")
                logger.info(f"Terminating active daemon/dashboard process {pid}")
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.1)
                    try:
                        os.kill(pid, 0)
                    except OSError:
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


def choose_folder_native() -> str | None:
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
