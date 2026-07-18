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
    server_port: int = 0

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
        elif path.startswith("/js/"):
            self._handle_js_asset(path[len("/js/"):])
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"
        qs = self._parse_query()
        if path == "/api/model/toggle":
            self._handle_model_toggle(qs.get("action", ""))
        elif path == "/api/dirs/choose":
            self._handle_choose_dir()
        elif path == "/api/dirs/select":
            self._handle_select_dir()
        else:
            self._send_json(404, {"error": "Not found"})

    def _handle_dirs(self, root_path: str) -> None:
        try:
            base = Path(root_path).resolve()
            # Security: restrict directory listing to the project root and its children.
            project = Path(self.project_path).resolve()
            try:
                base.relative_to(project)
            except ValueError:
                # Allow navigating to parent of project (for project-picker UI)
                # but never above the drive root or to unrelated paths.
                try:
                    project.relative_to(base)
                except ValueError:
                    self._send_json(200, {"current": str(base), "dirs": [], "error": "Path outside project scope"})
                    return
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
                "db_status": "missing",
                "message": f"No usage.db at {DB_PATH}",
            })
            return
        qs = self._parse_query()
        window = qs.get("window", "24h")
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            data = _query_stats(conn, window=window)
            conn.close()
            # Inject active server config
            data["project_path"] = DashboardHandler.project_path
            data["server_port"] = DashboardHandler.server_port
            data["db_status"] = "ok"
            data["version"] = __version__
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

    def _handle_asset(self, name: str, mime_type: str, subdir: str = "") -> None:
        from ._dashboard_shared import DASHBOARD_DIR
        try:
            base = DASHBOARD_DIR / subdir if subdir else DASHBOARD_DIR
            content = (base / name).read_text(encoding="utf-8")
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

    def _handle_js_asset(self, rel: str) -> None:
        from ._dashboard_shared import DASHBOARD_DIR
        import posixpath
        rel = posixpath.normpath(rel).lstrip("/")
        if rel != posixpath.basename(rel) and "/" not in rel.replace("\\", "/"):
            pass
        full = (DASHBOARD_DIR / "js" / rel).resolve()
        base = DASHBOARD_DIR.resolve()
        if base not in full.parents and full != base:
            self._send_json(403, {"error": "Forbidden"})
            return
        if not full.is_file():
            self._send_json(404, {"error": "Not found"})
            return
        self._handle_asset(rel, "application/javascript", subdir="js")

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
            DashboardHandler.project_path = path
            self._send_json(200, {"success": True, "path": path})
        else:
            self._send_json(200, {"success": False, "reason": "Native chooser failed or cancelled"})

    def _handle_select_dir(self) -> None:
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length else ""
        try:
            params = json.loads(body)
        except Exception:
            params = {}
        path = params.get("path")
        if not path:
            qs = self._parse_query()
            path = qs.get("path")
        if path:
            resolved_path = str(Path(path).expanduser().resolve())
            if Path(resolved_path).is_dir():
                DashboardHandler.project_path = resolved_path
                self._send_json(200, {"success": True, "path": resolved_path})
            else:
                self._send_json(400, {"error": f"Path is not a directory: {path}"})
        else:
            self._send_json(400, {"error": "Missing path parameter"})

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("  <= %s", format % args)


def _query_stats(conn: sqlite3.Connection, window: str = "24h") -> dict[str, Any]:
    """Aggregate usage data. window="24h" filters to the last 24h, "all" uses lifetime."""
    cur = conn.cursor()

    now = int(time.time())
    cutoff_24h = now - 86400
    window_filter = "" if window == "all" else "WHERE started_at >= ?"

    # Auto-cleanup: drop entries older than 24h
    cur.execute("DELETE FROM tool_calls WHERE started_at < ?", (cutoff_24h,))

    params = () if window == "all" else (cutoff_24h,)
    cur.execute(
        """SELECT tool_name, operation, COUNT(*) AS cnt,
                  COALESCE(SUM(tokens_original), 0) AS tok_orig,
                  COALESCE(SUM(tokens_optimized), 0) AS tok_opt
           FROM tool_calls {wf}
           GROUP BY tool_name, operation ORDER BY cnt DESC""".format(wf=window_filter),
        params,
    )
    tool_breakdown = [dict(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT skill_id, COUNT(*) AS cnt FROM skill_loads GROUP BY skill_id ORDER BY cnt DESC LIMIT 20"
    )
    top_skills = [dict(r) for r in cur.fetchall()]

    cur.execute(
        """SELECT tool_name, operation, started_at, duration_ms,
                  tokens_original, tokens_optimized, error_message
           FROM tool_calls {wf}
           ORDER BY started_at DESC LIMIT 20""".format(wf=window_filter),
        params,
    )
    recent_actions = [dict(r) for r in cur.fetchall()]

    cur.execute(
        """SELECT id, queried_at, status, vector_dim, result_count
           FROM embed_queries
           ORDER BY queried_at DESC LIMIT 20"""
    )
    embed_recent = [dict(r) for r in cur.fetchall()]

    # Hourly savings: 24 nodes, one per local hour bucket in the last 24h.
    cur.execute(
        """SELECT (started_at / 3600) AS hr_bucket,
                  COALESCE(SUM(tokens_original), 0) AS original,
                  COALESCE(SUM(tokens_optimized), 0) AS optimized,
                  COALESCE(SUM(tokens_original), 0) - COALESCE(SUM(tokens_optimized), 0) AS saved
           FROM tool_calls
           WHERE started_at >= ?
           GROUP BY hr_bucket""",
        (cutoff_24h,),
    )
    bucket_data: dict[int, dict[str, int]] = {r["hr_bucket"]: dict(r) for r in cur.fetchall()}

    now = int(time.time())
    current_hour = now // 3600
    # 24 sequential hourly buckets ending at the current hour, so the last
    # column is always the current hour (column 0 is ~24h ago).
    hourly_savings = []
    for i in range(24):
        bucket = (current_hour - 23) + i
        bdata = bucket_data.get(bucket, {"original": 0, "optimized": 0, "saved": 0})
        bucket_start = bucket * 3600
        date_label = time.strftime("%Y-%m-%d", time.localtime(bucket_start))
        hourly_savings.append({
            "hour": bucket % 24,
            "date": date_label,
            "original": bdata["original"],
            "optimized": bdata["optimized"],
            "saved": bdata["saved"],
            "is_current": bucket == current_hour,
        })

    cur.execute("SELECT COUNT(*) AS total FROM tool_calls")
    total_calls = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM skill_loads")
    total_skills = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM embed_queries")
    total_embeds = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM llm_queries")
    total_llm = cur.fetchone()["total"]

    tot_orig = sum(r.get("tok_orig", 0) for r in tool_breakdown)
    tot_opt = sum(r.get("tok_opt", 0) for r in tool_breakdown)
    token_savings = tot_orig - tot_opt
    savings_pct = round((token_savings / max(1, tot_orig)) * 100, 1)

    return {
        "totals": {
            "tool_calls": total_calls,
            "skills_loaded": total_skills,
            "embed_queries": total_embeds,
            "llm_queries": total_llm,
            "tokens_original": tot_orig,
            "tokens_optimized": tot_opt,
            "token_savings": token_savings,
            "savings_pct": savings_pct,
        },
        "tool_breakdown": tool_breakdown,
        "top_skills": top_skills,
        "recent_actions": recent_actions,
        "hourly_savings": hourly_savings,
        "embed_recent": embed_recent,
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
    from ._dashboard_shared import (
        DAEMON_DIR,
        DAEMON_PORT_FILE,
        DASHBOARD_PORT_FILE,
        kill_existing_dashboard,
    )

    daemon_alive = False
    if DAEMON_PORT_FILE.is_file():
        try:
            manifest = json.loads(DAEMON_PORT_FILE.read_text(encoding="utf-8"))
            pid = manifest.get("pid")
            port = manifest.get("port")
            # Prefer an HTTP /health probe (reliable on Windows, where
            # os.kill(pid, 0) raises for permission mismatches on live PIDs).
            if port is not None:
                try:
                    import httpx

                    r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                    if r.is_success:
                        daemon_alive = True
                except Exception:
                    pass
            if not daemon_alive and pid:
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
        # Only ever kill a previous *dashboard* instance, never the shared
        # embedding daemon (which lives in daemon.json).
        kill_existing_dashboard()

    pp = project_path or os.environ.get("AGENT_PROJECT_ROOT", os.getcwd())
    pp = str(Path(pp).resolve())

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    DashboardHandler.project_path = pp
    DashboardHandler.db_path = str(DB_PATH)
    DashboardHandler.server_port = port

    if not daemon_alive:
        DAEMON_DIR.mkdir(parents=True, exist_ok=True)
        DASHBOARD_PORT_FILE.write_text(
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
