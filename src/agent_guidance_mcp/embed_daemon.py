"""Lightweight HTTP daemon for SentenceTransformer inference.

Serves `/embed` POST endpoint. Auto-detects free port, writes manifest
to ~/.agent-guidance/daemon.json for client discovery. Background reaper
exits daemon when all registered clients die or idle timeout reached.
"""
from __future__ import annotations

import errno
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent-guidance-mcp.daemon")

from ._dashboard_shared import DAEMON_DIR, DAEMON_PORT_FILE, DASHBOARD_DIR
IDLE_TIMEOUT_S = 600
GRACE_AFTER_EMPTY_S = 30
HEALTH_CHECK_INTERVAL = 15

_E5_MODEL = "intfloat/multilingual-e5-small"

# ── Port detection (TOCTOU-safe: bind port 0, keep FD) ──────────────────


def _bind_loopback_fd() -> tuple[socket.socket, int] | None:
    """Bind to 127.0.0.1 on OS-assigned port. Returns (socket, port).

    Using OS-assigned port (bind port 0) eliminates the TOCTOU race of
    bind-and-close-then-rebind.
    """
    for _ in range(3):  # retry on transient EADDRNOTAVAIL
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            return (s, port)
        except OSError as e:
            s.close()
            if e.errno != errno.EADDRINUSE:
                raise
            continue
    return None


# ── Manifest I/O ────────────────────────────────────────────────────────


def _write_manifest(port: int, pid: int) -> None:
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    DAEMON_PORT_FILE.write_text(
        json.dumps({"port": port, "pid": pid, "started_at": time.time()}), encoding="utf-8"
    )


def _read_manifest() -> dict[str, Any] | None:
    if not DAEMON_PORT_FILE.is_file():
        return None
    try:
        return json.loads(DAEMON_PORT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _clean_manifest() -> None:
    try:
        DAEMON_PORT_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# ── FastAPI app ─────────────────────────────────────────────────────────

_model: Any = None

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel
    import uvicorn

    class EmbedRequest(BaseModel):
        text: str
        prefix: str | None = None

    class EmbedResponse(BaseModel):
        vector: list[float]

    class RegisterRequest(BaseModel):
        client_id: str
        pid: int

    class UnregisterRequest(BaseModel):
        client_id: str

    app = FastAPI(title="embedding-daemon")
    _clients: dict[str, int] = {}
    _last_embed_time: float = time.time()
    _start_time: float = time.time()
    _clients_lock = threading.Lock()
    _FASTAPI_AVAILABLE = True

except ImportError:
    class _DummyApp:
        _decorated: list = []
        def __getattr__(self, _name: str) -> object:
            def _deco(*a: object, **kw: object) -> object:
                return lambda f: (_decorated.append(f), f)[1]
            return _deco
    app = _DummyApp()
    _FASTAPI_AVAILABLE = False


@app.post("/register")
def register(req: RegisterRequest) -> dict:
    with _clients_lock:
        _clients[req.client_id] = req.pid
        n = len(_clients)
    logger.info("client %s (pid %d) registered — %d client(s) active", req.client_id, req.pid, n)
    return {"ok": True, "clients": n}


@app.post("/unregister")
def unregister(req: UnregisterRequest) -> dict:
    with _clients_lock:
        _clients.pop(req.client_id, None)
        n = len(_clients)
    logger.info("client %s unregistered — %d client(s) active", req.client_id, n)
    return {"ok": True, "clients": n}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    global _model, _last_embed_time
    if _model is None:
        _load_model()
    _last_embed_time = time.time()
    text = req.text
    if req.prefix == "query":
        text = "query: " + text
    elif req.prefix == "passage":
        text = "passage: " + text
    vector = _model.encode(text, normalize_embeddings=True)
    return EmbedResponse(vector=vector.tolist())


@app.get("/api/stats")
def stats() -> dict:
    """Return aggregated usage stats from the global usage.db."""
    from .usage import DB_PATH

    if not DB_PATH.exists():
        return {
            "success": False,
            "error": "NO_USAGE_DATA",
            "message": f"No usage.db found at {DB_PATH}. Usage tracking may not be active.",
        }

    try:
        from .usage import UsageTracker as _UsageTracker
    except ImportError:
        from agent_guidance_mcp.usage import UsageTracker as _UsageTracker

    tracker = _UsageTracker()
    try:
        return tracker.summary()
    finally:
        tracker.close()


@app.get("/")
def dashboard() -> HTMLResponse:
    """Serve the usage dashboard HTML."""
    from ._dashboard_shared import DASHBOARD_DIR, write_default_dashboard
    write_default_dashboard(None)
    index_path = DASHBOARD_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            content="<h1>Dashboard files not found</h1>",
            status_code=500,
        )
    content = index_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/dashboard.css")
def css() -> Response:
    from fastapi import Response
    from ._dashboard_shared import DASHBOARD_DIR
    css_path = DASHBOARD_DIR / "dashboard.css"
    if not css_path.exists():
        return Response(content="", status_code=404)
    return Response(
        content=css_path.read_text(encoding="utf-8"),
        media_type="text/css",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/dashboard.js")
def js() -> Response:
    from fastapi import Response
    from ._dashboard_shared import DASHBOARD_DIR
    js_path = DASHBOARD_DIR / "dashboard.js"
    if not js_path.exists():
        return Response(content="", status_code=404)
    return Response(
        content=js_path.read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.post("/api/model/toggle")
def toggle_model(action: str) -> dict:
    global _model
    if action == "unload":
        if _model is not None:
            _model = None
            import gc
            gc.collect()
            logger.info("SentenceTransformer model unloaded from memory")
        return {"success": True, "model_loaded": False}
    elif action == "load":
        if _model is None:
            _load_model()
        return {"success": True, "model_loaded": True}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid action parameter, must be 'load' or 'unload'")


@app.get("/api/dirs")
def list_directories(path: str = ".") -> dict:
    from pathlib import Path
    try:
        base = Path(path).resolve()
        if not base.is_dir():
            return {"current": str(base), "dirs": [], "error": "Not a directory"}
        entries = []
        for entry in sorted(base.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                try:
                    entries.append({"name": entry.name, "path": str(entry.resolve())})
                except OSError:
                    pass
        parent = str(base.parent) if base.parent != base else None
        return {"current": str(base), "parent": parent, "dirs": entries}
    except (OSError, PermissionError) as e:
        return {"current": path, "dirs": [], "error": str(e)}


@app.post("/api/dirs/choose")
def choose_directory() -> dict:
    from ._dashboard_shared import choose_folder_native
    path = choose_folder_native()
    if path:
        return {"success": True, "path": path}
    return {"success": False, "reason": "Native chooser failed or cancelled"}


@app.get("/health")
def health() -> dict:
    with _clients_lock:
        n = len(_clients)
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "clients": n,
        "engine": _E5_MODEL,
        "uptime_seconds": int(time.time() - _start_time),
        "last_embed_time": _last_embed_time,
    }


# ── Model loading ───────────────────────────────────────────────────────


def _load_model() -> None:
    global _model
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
    from sentence_transformers import SentenceTransformer

    local_files_only = "pytest" in sys.modules or os.environ.get("HF_HUB_OFFLINE", "0") == "1"
    logger.info("loading %s (local_files_only=%s)", _E5_MODEL, local_files_only)
    _model = SentenceTransformer(_E5_MODEL, local_files_only=local_files_only)
    logger.info("model loaded")


# ── Background reaper ───────────────────────────────────────────────────


def _reaper() -> None:
    """Background thread that exits daemon when no clients remain or idle."""
    empty_since: float | None = None
    while True:
        time.sleep(HEALTH_CHECK_INTERVAL)

        # Check idle timeout
        elapsed = time.time() - _last_embed_time
        if elapsed > IDLE_TIMEOUT_S:
            logger.info("idle %ds — exiting", int(elapsed))
            _clean_manifest()
            os._exit(0)

        # Check client liveness
        with _clients_lock:
            pids = dict(_clients)

        if not pids:
            if empty_since is None:
                empty_since = time.time()
            elif time.time() - empty_since > GRACE_AFTER_EMPTY_S:
                logger.info("no clients for %ds — exiting", GRACE_AFTER_EMPTY_S)
                _clean_manifest()
                os._exit(0)
            continue

        empty_since = None
        for cid, pid in list(pids.items()):
            try:
                os.kill(pid, 0)
            except OSError:
                logger.info("client %s (pid %d) dead — removing", cid, pid)
                with _clients_lock:
                    _clients.pop(cid, None)


# ── Signal handling ─────────────────────────────────────────────────────


def _signal_handler(signum: int, _frame: object) -> None:
    logger.info("received signal %d — cleaning up manifest", signum)
    _clean_manifest()
    sys.exit(0)


from ._dashboard_shared import write_default_dashboard as _write_default_dashboard

# ── Entry point ─────────────────────────────────────────────────────────


def main() -> None:
    from ._dashboard_shared import kill_existing_daemon
    kill_existing_daemon()

    if not _FASTAPI_AVAILABLE:
        print("Error: fastapi and uvicorn are required for the embedding daemon.", file=sys.stderr)
        print("Install with: pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)
    result = _bind_loopback_fd()
    if result is None:
        logger.error("failed to bind loopback socket")
        sys.exit(1)
    sock, port = result

    _write_manifest(port, os.getpid())
    logger.info("daemon starting on 127.0.0.1:%d (pid %d)", port, os.getpid())

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    t = threading.Thread(target=_reaper, daemon=True)
    t.start()

    uvicorn.run(app, fd=sock.fileno(), log_config=None)


if __name__ == "__main__":
    main()
