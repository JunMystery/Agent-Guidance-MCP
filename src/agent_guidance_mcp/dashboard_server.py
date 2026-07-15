"""Lightweight standalone HTTP server for the usage dashboard.

Pure stdlib — no fastapi, no uvicorn, no ML model.
Reads usage.db from a project path and serves the dashboard HTML.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sqlite3
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from . import __version__
from .usage import DB_PATH

logger = logging.getLogger("agent-guidance-mcp.dashboard")


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler serving dashboard API and HTML."""

    # Shared reference — set by run_dashboard()
    project_path: str = ""
    db_path: str = ""

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path == "/api/stats":
            self._handle_stats()
        elif path == "/api/dirs":
            qs = self._parse_query()
            self._handle_dirs(qs.get("path", "."))
        elif path == "/health":
            self._handle_health()
        elif path in ("/", "/index.html"):
            self._handle_dashboard()
        elif path == "/dashboard.css":
            self._handle_asset("dashboard.css", "text/css")
        elif path == "/dashboard.js":
            self._handle_asset("dashboard.js", "application/javascript")
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"
        qs = self._parse_query()
        if path == "/api/model/toggle":
            self._handle_model_toggle(qs.get("action", ""))
        elif path == "/api/dirs/choose":
            self._handle_choose_dir()
        else:
            self._send_json(404, {"error": "Not found"})

    def _handle_dirs(self, root_path: str) -> None:
        try:
            base = Path(root_path).resolve()
            if not base.is_dir():
                self._send_json(200, {"current": str(base), "dirs": [], "error": "Not a directory"})
                return
            entries = []
            for entry in sorted(base.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    try:
                        entries.append({"name": entry.name, "path": str(entry.resolve())})
                    except OSError:
                        pass
            parent = str(base.parent) if base.parent != base else None
            self._send_json(200, {"current": str(base), "parent": parent, "dirs": entries})
        except (OSError, PermissionError) as e:
            self._send_json(200, {"current": root_path, "dirs": [], "error": str(e)})

    def _parse_query(self) -> dict[str, str]:
        qs = self.path.split("?", 1)[1] if "?" in self.path else ""
        params: dict[str, str] = {}
        if qs:
            for part in qs.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    from urllib.parse import unquote_plus
                    params[unquote_plus(k)] = unquote_plus(v)
        return params

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _handle_stats(self) -> None:
        if not DB_PATH.exists():
            self._send_json(200, {
                "success": False, "error": "NO_USAGE_DATA",
                "message": f"No usage.db at {DB_PATH}",
            })
            return
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            data = _query_stats(conn)
            conn.close()
            self._send_json(200, data)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_health(self) -> None:
        daemon_health = _query_daemon("/health")
        if daemon_health:
            self._send_json(200, {
                "status": "ok",
                "server": "agent-guidance-mcp-dashboard",
                "version": __version__,
                "model_loaded": daemon_health.get("model_loaded", False),
                "clients": daemon_health.get("clients", 0),
                "engine": daemon_health.get("engine", "unknown"),
                "uptime_seconds": daemon_health.get("uptime_seconds", 0),
                "last_embed_time": daemon_health.get("last_embed_time", 0),
            })
        else:
            self._send_json(200, {
                "status": "ok",
                "server": "agent-guidance-mcp-dashboard",
                "version": __version__,
                "model_loaded": False,
                "clients": 0,
                "engine": "unknown",
                "uptime_seconds": 0,
                "last_embed_time": 0,
            })

    def _handle_dashboard(self) -> None:
        from ._dashboard_shared import DASHBOARD_DIR, write_default_dashboard
        write_default_dashboard(None)
        index_path = DASHBOARD_DIR / "index.html"
        if not index_path.exists():
            self._send_json(500, {"error": "Dashboard files not found"})
            return
        content = index_path.read_text(encoding="utf-8")
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _handle_asset(self, name: str, mime_type: str) -> None:
        from ._dashboard_shared import DASHBOARD_DIR
        try:
            content = (DASHBOARD_DIR / name).read_text(encoding="utf-8")
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
        except Exception as e:
            self._send_json(500, {"error": f"Failed to load asset {name}: {e}"})

    def _handle_model_toggle(self, action: str) -> None:
        daemon_resp = _query_daemon(f"/api/model/toggle?action={action}", method="POST")
        if daemon_resp:
            self._send_json(200, daemon_resp)
        else:
            self._send_json(503, {"error": "Embedding daemon not running or unreachable"})

    def _handle_choose_dir(self) -> None:
        from ._dashboard_shared import choose_folder_native
        path = choose_folder_native()
        if path:
            self._send_json(200, {"success": True, "path": path})
        else:
            self._send_json(200, {"success": False, "reason": "Native chooser failed or cancelled"})

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("  <= %s", format % args)


def _query_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Aggregate all usage data (no session filter)."""
    cur = conn.cursor()

    cur.execute(
        """SELECT tool_name, operation, COUNT(*) AS cnt,
                  COALESCE(SUM(tokens_original), 0) AS tok_orig,
                  COALESCE(SUM(tokens_optimized), 0) AS tok_opt
           FROM tool_calls
           GROUP BY tool_name, operation ORDER BY cnt DESC"""
    )
    tool_breakdown = [dict(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT skill_id, COUNT(*) AS cnt FROM skill_loads GROUP BY skill_id ORDER BY cnt DESC LIMIT 20"
    )
    top_skills = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*) AS total FROM tool_calls")
    total_calls = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM skill_loads")
    total_skills = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM embed_queries")
    total_embeds = cur.fetchone()["total"]

    tot_orig = sum(r.get("tok_orig", 0) for r in tool_breakdown)
    tot_opt = sum(r.get("tok_opt", 0) for r in tool_breakdown)
    token_savings = tot_orig - tot_opt
    savings_pct = round((token_savings / max(1, tot_orig)) * 100, 1)

    return {
        "totals": {
            "tool_calls": total_calls,
            "skills_loaded": total_skills,
            "embed_queries": total_embeds,
            "tokens_original": tot_orig,
            "tokens_optimized": tot_opt,
            "token_savings": token_savings,
            "savings_pct": savings_pct,
        },
        "tool_breakdown": tool_breakdown,
        "top_skills": top_skills,
    }


def _query_daemon(path: str, method: str = "GET") -> dict | None:
    from ._dashboard_shared import DAEMON_PORT_FILE
    import urllib.request
    import json
    if not DAEMON_PORT_FILE.is_file():
        return None
    try:
        manifest = json.loads(DAEMON_PORT_FILE.read_text(encoding="utf-8"))
        if manifest.get("mode") == "dashboard":
            return None
        port = manifest.get("port")
        if not port:
            return None
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method)
        with urllib.request.urlopen(req, timeout=1.0) as r:
            if r.status == 200:
                return json.loads(r.read().decode("utf-8"))
    except Exception:
        pass
    return None


def run_dashboard(project_path: str | None = None) -> None:
    """Start the dashboard HTTP server.

    Reads usage.db from project_path, serves dashboard at http://127.0.0.1:<port>/.
    """
    from ._dashboard_shared import DAEMON_DIR, DAEMON_PORT_FILE, kill_existing_daemon

    daemon_alive = False
    if DAEMON_PORT_FILE.is_file():
        try:
            manifest = json.loads(DAEMON_PORT_FILE.read_text(encoding="utf-8"))
            if manifest.get("mode") != "dashboard":
                pid = manifest.get("pid")
                if pid:
                    try:
                        os.kill(pid, 0)
                        daemon_alive = True
                    except OSError:
                        pass
        except Exception:
            pass

    if daemon_alive:
        logger.info("Embed daemon already running — dashboard will proxy requests to it")
    else:
        kill_existing_daemon()

    pp = project_path or os.environ.get("AGENT_PROJECT_ROOT", os.getcwd())
    pp = str(Path(pp).resolve())

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    DashboardHandler.project_path = pp
    DashboardHandler.db_path = str(DB_PATH)

    if not daemon_alive:
        DAEMON_DIR.mkdir(parents=True, exist_ok=True)
        DAEMON_PORT_FILE.write_text(
            json.dumps({"port": port, "pid": os.getpid(), "started_at": time.time(), "mode": "dashboard"}),
            encoding="utf-8",
        )
    else:
        logger.info("daemon.json preserved — proxy to embed daemon active")

    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    url = f"http://127.0.0.1:{port}/"
    logger.info("dashboard server started on %s (project: %s)", url, pp)
    print(f"\n  Dashboard: {url}\n", flush=True)
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        logger.info("dashboard server stopped")
