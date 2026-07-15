import atexit
import fcntl
import json
import logging
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("agent-guidance-mcp.embeddings")

_DAEMON_PORT: int | None = None
_DAEMON_CLIENT_ID: str | None = None
_DAEMON_FAILED = False

_DAEMON_DIR = Path.home() / ".agent-guidance"
_DAEMON_PORT_FILE = _DAEMON_DIR / "daemon.json"

_E5_MODEL = "intfloat/multilingual-e5-small"

# ── In-process fallback model (loaded only when daemon unavailable) ──────

_model: Any = None
_model_lock = threading.Lock()


def get_embedding_model() -> Optional[Any]:
    """Return the in-process SentenceTransformer model (fallback / pre-download).

    Used by pre_download_models() to cache model files. For actual embedding
    inference, prefer get_embedding() which uses the shared daemon.
    """
    global _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
            os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading {_E5_MODEL} model...")
            local_files_only = ("pytest" in sys.modules) or (os.environ.get("HF_HUB_OFFLINE", "0") == "1")
            _model = SentenceTransformer(_E5_MODEL, local_files_only=local_files_only)
            return _model
        except ImportError:
            logger.warning(
                "The 'sentence-transformers' package is not installed. "
                "Local dynamic embeddings will be disabled and will fall back to keyword search."
            )
            return None
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            return None


def pre_download_models() -> bool:
    """Pre-download the embedding model so daemon start doesn't trigger a download."""
    model = get_embedding_model()
    return model is not None


def _in_process_get_embedding(text: str, prefix: str | None = None) -> Optional[List[float]]:
    """Fallback embedding using in-process model (when daemon unavailable)."""
    model = get_embedding_model()
    if model is None:
        return None
    try:
        if prefix == "query":
            text = "query: " + text
        elif prefix == "passage":
            text = "passage: " + text
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return None


# ── Daemon client ───────────────────────────────────────────────────────


_ARGS = (sys.executable, "-m", "agent_guidance_mcp.embed_daemon")
_SPAWN_WAIT_S = 4.0
_SPAWN_POLL_S = 0.2


def _client_id() -> str:
    global _DAEMON_CLIENT_ID
    if _DAEMON_CLIENT_ID is None:
        _DAEMON_CLIENT_ID = f"mcp-{os.getpid()}"
    return _DAEMON_CLIENT_ID


_DAEMON_LOCK_FILE = _DAEMON_DIR / "daemon.lock"


def _acquire_daemon_lock() -> int | None:
    """Acquire exclusive file lock on daemon.lock. Returns fd or None.

    Prevents two concurrent MCP processes from both spawning a daemon.
    The lock is released when the fd is closed (explicitly or on process exit).
    """
    _DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(_DAEMON_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (IOError, OSError):
        try:
            os.close(fd)
        except (OSError, NameError):
            pass
        return None


def _read_manifest() -> dict[str, Any] | None:
    if not _DAEMON_PORT_FILE.is_file():
        return None
    try:
        return json.loads(_DAEMON_PORT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _spawn_daemon() -> int | None:
    """Start the embedding daemon subprocess and return its port."""
    logger.info("spawning embedding daemon")
    try:
        subprocess.Popen(
            _ARGS,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("failed to spawn daemon: %s", e)
        return None

    # Wait for manifest to appear and HTTP server to respond
    deadline = time.time() + _SPAWN_WAIT_S
    while time.time() < deadline:
        time.sleep(_SPAWN_POLL_S)
        manifest = _read_manifest()
        if manifest is not None:
            port = manifest.get("port")
            pid = manifest.get("pid")
            if isinstance(port, int) and isinstance(pid, int):
                # Verify daemon process is alive
                try:
                    os.kill(pid, 0)
                except OSError:
                    logger.warning("daemon pid %d died, retrying spawn", pid)
                    continue
                # Confirm HTTP server is actually accepting connections
                try:
                    r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                    if r.is_success:
                        logger.info("daemon running on port %d (pid %d)", port, pid)
                        return port
                except httpx.RequestError:
                    pass  # daemon not ready yet, retry
    logger.warning("daemon did not start within %.1fs", _SPAWN_WAIT_S)
    return None


def _ensure_daemon() -> int | None:
    """Return daemon port, spawning daemon if needed.

    Uses a file lock (daemon.lock) to prevent concurrent spawns when
    two MCP processes start simultaneously.
    """
    global _DAEMON_PORT, _DAEMON_FAILED

    if _DAEMON_PORT is not None:
        return _DAEMON_PORT
    if _DAEMON_FAILED:
        return None

    # Skip daemon in test environments
    if "pytest" in sys.modules or os.environ.get("AGENT_EMBEDDING_DAEMON") == "0":
        _DAEMON_FAILED = True
        return None

    lock_fd = _acquire_daemon_lock()
    if lock_fd is None:
        # Another process is spawning — wait for its manifest
        deadline = time.time() + _SPAWN_WAIT_S
        while time.time() < deadline:
            time.sleep(_SPAWN_POLL_S)
            manifest = _read_manifest()
            if manifest:
                port = manifest.get("port")
                pid = manifest.get("pid")
                if isinstance(port, int) and isinstance(pid, int):
                    try:
                        os.kill(pid, 0)
                        _DAEMON_PORT = port
                        _register()
                        return port
                    except OSError:
                        continue
        _DAEMON_FAILED = True
        logger.warning("another process's daemon did not start within %.1fs", _SPAWN_WAIT_S)
        return None

    try:
        manifest = _read_manifest()
        if manifest:
            port = manifest.get("port")
            pid = manifest.get("pid")
            if isinstance(port, int) and isinstance(pid, int):
                try:
                    os.kill(pid, 0)
                    logger.info("reusing existing daemon on port %d (pid %d)", port, pid)
                    _DAEMON_PORT = port
                    _register()
                    return port
                except OSError:
                    logger.info("daemon pid %d dead — spawning new one", pid)

        port = _spawn_daemon()
        if port is not None:
            _DAEMON_PORT = port
            _register()
            return port

        _DAEMON_FAILED = True
        logger.warning("daemon unavailable — falling back to in-process model")
        return None
    finally:
        os.close(lock_fd)


def _register() -> None:
    cid = _client_id()
    pid = os.getpid()
    try:
        resp = httpx.post(
            f"http://127.0.0.1:{_DAEMON_PORT}/register",
            json={"client_id": cid, "pid": pid},
            timeout=3.0,
        )
        if resp.is_success:
            logger.debug("registered with daemon (cid=%s, pid=%d)", cid, pid)
    except httpx.RequestError as e:
        logger.warning("failed to register with daemon: %s", e)


def _unregister_daemon() -> None:
    if _DAEMON_PORT is None:
        return
    cid = _client_id()
    try:
        httpx.post(
            f"http://127.0.0.1:{_DAEMON_PORT}/unregister",
            json={"client_id": cid},
            timeout=2.0,
        )
    except httpx.RequestError:
        pass


atexit.register(_unregister_daemon)


# ── Public embedding API ────────────────────────────────────────────────


_E5_QUERY_PREFIX = "query: "
_E5_PASSAGE_PREFIX = "passage: "


def get_embedding(text: str, prefix: str | None = None) -> Optional[List[float]]:
    """Generate embedding via shared daemon, falling back to in-process."""
    port = _ensure_daemon()

    # Try daemon
    if port is not None:
        try:
            resp = httpx.post(
                f"http://127.0.0.1:{port}/embed",
                json={"text": text, "prefix": prefix},
                timeout=30.0,
            )
            if resp.is_success:
                return resp.json()["vector"]
            logger.warning("daemon returned %d — falling back", resp.status_code)
        except httpx.RequestError as e:
            logger.warning("daemon request failed: %s — falling back", e)

    # Fallback to in-process
    return _in_process_get_embedding(text, prefix)


# ── Vector math (no change) ─────────────────────────────────────────────


def dot_product(v1: List[float], v2: List[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))


def magnitude(v: List[float]) -> float:
    return math.sqrt(sum(a * a for a in v))


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product(v1, v2) / (mag1 * mag2)


def load_precomputed_embeddings() -> Dict[str, List[float]]:
    """Load pre-computed embeddings from the bundled package file."""
    try:
        path = Path(__file__).resolve().parent / "skills_embeddings.json"
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load pre-computed embeddings: {e}")
    return {}
