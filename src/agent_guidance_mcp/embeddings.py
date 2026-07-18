import atexit
import hashlib
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
_EMBEDDING_BACKEND = "unknown"

_DAEMON_DIR = Path.home() / ".agent-guidance"
_DAEMON_PORT_FILE = _DAEMON_DIR / "daemon.json"
_DAEMON_LOG = _DAEMON_DIR / "daemon.log"

_E5_MODEL = "intfloat/multilingual-e5-small"

# Expected embedding dimension for the bundled e5-small model. Used as a
# defensive guard so a model swap / corrupted precomputed file degrades
# gracefully instead of producing garbage similarity (F6).
EXPECTED_DIM = 384
# Reserved top-level key in skills_embeddings.json holding hashes for staleness
# detection (F2) and content-hash auto-heal.
_META_KEY = "__meta__"
_EMBEDDINGS_FILE = Path(__file__).resolve().parent / "skills_embeddings.json"

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
            local_files_only = (
                ("pytest" in sys.modules)
                or (os.environ.get("HF_HUB_OFFLINE", "0") == "1")
                or _model_already_cached(_E5_MODEL)
            )
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


def _model_already_cached(repo_id: str) -> bool:
    """Return True if a model repo is fully present in the local HF hub cache.

    Lets pre_download_models()/pre_download_llm() skip the heavy in-memory load
    when the weights are already on disk (e.g. a re-run of the installer or
    `--update`). Any failure to determine cache state falls through to a real
    load attempt rather than erroring out.
    """
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id, local_files_only=True)
        return True
    except Exception:
        return False


def pre_download_models() -> bool:
    """Pre-download the embedding model so daemon start doesn't trigger a download.

    Skips the in-memory load entirely when the model is already cached, so a
    re-run of `--update` (or the installer) is fast and offline-safe.
    """
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError:
        logger.warning(
            "The 'sentence-transformers' package is not installed. "
            "Local dynamic embeddings will be disabled and will fall back to keyword search."
        )
        return False
    if _model_already_cached(_E5_MODEL):
        logger.info("Embedding model already cached, skipping load: %s", _E5_MODEL)
        return True
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


try:
    import fcntl as _fcntl
    _HAVE_FCNTL = True
except ImportError:
    _fcntl = None  # type: ignore[assignment]
    _HAVE_FCNTL = False

try:
    import msvcrt as _msvcrt
    _HAVE_MSVCRT = True
except ImportError:
    _msvcrt = None  # type: ignore[assignment]
    _HAVE_MSVCRT = False


def _acquire_daemon_lock() -> int | None:
    """Acquire an exclusive cross-platform file lock on daemon.lock.

    Returns a lock handle (int fd on POSIX, file object on Windows) that must
    be closed to release the lock, or ``None`` if the lock is already held by
    another process (non-blocking).

    Prevents two concurrent MCP processes from both spawning a daemon. This is
    **not** a no-op on Windows anymore: it uses ``msvcrt.locking`` so the
    spawn de-duplication actually works on Windows (previously the lock was a
    silent no-op, allowing N OpenCode CLIs to each spawn their own embedding
    daemon).
    """
    _DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if _HAVE_FCNTL:
            fd = os.open(_DAEMON_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
            try:
                _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
                return None
            return fd
        if _HAVE_MSVCRT:
            handle = open(_DAEMON_LOCK_FILE, "w+", encoding="utf-8")
            try:
                _msvcrt.locking(handle.fileno(), _msvcrt.LK_NBLCK, 1)
            except OSError:
                handle.close()
                return None
            _WIN_LOCK_HANDLES[id(handle)] = handle
            return id(handle)  # sentinel; real release uses _release_daemon_lock
    except OSError:
        return None
    return None


def _release_daemon_lock(lock: int | None) -> None:
    """Release a lock previously acquired by :func:`_acquire_daemon_lock`.

    On POSIX ``lock`` is the open fd; on Windows it is a sentinel and the
    underlying file object is tracked in ``_WIN_LOCK_HANDLES``.
    """
    if lock is None:
        return
    if _HAVE_FCNTL:
        try:
            os.close(lock)
        except OSError:
            pass
        return
    if _HAVE_MSVCRT:
        handle = _WIN_LOCK_HANDLES.pop(lock, None)
        if handle is not None:
            try:
                _msvcrt.locking(handle.fileno(), _msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            try:
                handle.close()
            except OSError:
                pass


_WIN_LOCK_HANDLES: dict[int, object] = {}


def _read_manifest() -> dict[str, Any] | None:
    if not _DAEMON_PORT_FILE.is_file():
        return None
    try:
        return json.loads(_DAEMON_PORT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _spawn_daemon() -> int | None:
    """Start the embedding daemon subprocess and return its port.

    Returns ``None`` if the process could not be launched or did not become
    healthy in time. Failure here is non-fatal: the caller falls back to the
    in-process model instead of dropping the MCP connection.
    """
    logger.info("spawning embedding daemon")
    proc = None
    try:
        # F7: capture daemon logs to a file instead of discarding them, so a
        # crashed/misconfigured daemon is diagnosable.
        _DAEMON_DIR.mkdir(parents=True, exist_ok=True)
        with open(_DAEMON_LOG, "a", buffering=1) as log_fd:
            proc = subprocess.Popen(
                _ARGS,
                start_new_session=True,
                stdout=log_fd,
                stderr=log_fd,
            )
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("failed to spawn daemon: %s", e)
        return None

    # Wait for manifest to appear and the HTTP server to answer /health.
    deadline = time.time() + _SPAWN_WAIT_S
    while time.time() < deadline:
        time.sleep(_SPAWN_POLL_S)
        # Bail early if the child died before writing a manifest.
        if proc.poll() is not None:
            logger.warning("daemon subprocess exited early (code %s)", proc.returncode)
            return None
        manifest = _read_manifest()
        if manifest is not None:
            port = manifest.get("port")
            pid = manifest.get("pid")
            if _is_daemon_alive(port, pid):
                logger.info("daemon running on port %d (pid %d)", port, pid)
                return port
    logger.warning("daemon did not start within %.1fs", _SPAWN_WAIT_S)
    return None


def _is_daemon_alive(port: int, pid: int) -> bool:
    """Return True only if the recorded daemon PID is actually *our* daemon.

    Uses an HTTP ``/health`` probe (the daemon writes its real PID into
    daemon.json and answers on the recorded port) instead of ``os.kill(pid, 0)``,
    which is unreliable on Windows — there a permission mismatch (not just a
    dead PID) raises OSError, so a live daemon could be mis-detected as dead.
    """
    if not isinstance(port, int) or not isinstance(pid, int):
        return False
    try:
        r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
    except httpx.RequestError:
        return False
    if not r.is_success:
        return False
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    # The daemon echoes its own pid in /health so we can confirm identity and
    # avoid trusting a possibly-recycled PID recorded in the manifest.
    live_pid = body.get("pid")
    if isinstance(live_pid, int) and live_pid != pid:
        logger.warning("manifest pid %d != live daemon pid %d — manifest stale", pid, live_pid)
        return False
    # Only reuse once the daemon is actually serving /embed. The manifest is
    # published on the FastAPI startup event, so this also rejects any
    # not-yet-ready or non-embed server (e.g. the dashboard) that answers
    # /health without embed_ready.
    if not body.get("embed_ready"):
        return False
    return True


def _reuse_existing_daemon() -> int | None:
    """Reuse a live daemon described by daemon.json, or None."""
    manifest = _read_manifest()
    if not manifest:
        return None
    port = manifest.get("port")
    pid = manifest.get("pid")
    if _is_daemon_alive(port, pid):
        logger.info("reusing existing daemon on port %d (pid %d)", port, pid)
        return port
    logger.info("daemon pid %s dead/stale — will spawn a new one", pid)
    return None


def _ensure_daemon() -> int | None:
    """Return daemon port, spawning the daemon if needed.

    Guarantees at most one embedding daemon across all MCP processes:

    * A cross-platform exclusive file lock (``daemon.lock``) serializes spawn
      decisions. The lock holder either reuses a live daemon or spawns one and
      writes ``daemon.json`` *before* releasing the lock, so any later process
      observes the manifest under the lock (no TOCTOU double-spawn).
    * Processes that fail to acquire the lock wait for the holder to publish
      its manifest, then reuse it.

    Falls back to the in-process model if the daemon cannot be started.
    """
    global _DAEMON_PORT, _DAEMON_FAILED, _EMBEDDING_BACKEND

    if _DAEMON_PORT is not None:
        return _DAEMON_PORT
    if _DAEMON_FAILED:
        return None

    # Skip daemon in test environments
    if "pytest" in sys.modules or os.environ.get("AGENT_EMBEDDING_DAEMON") == "0":
        _DAEMON_FAILED = True
        return None

    lock = _acquire_daemon_lock()
    if lock is None:
        # Another process holds the lock and is (re)spawning — wait for its
        # manifest rather than racing it.
        deadline = time.time() + _SPAWN_WAIT_S
        while time.time() < deadline:
            time.sleep(_SPAWN_POLL_S)
            port = _reuse_existing_daemon()
            if port is not None:
                _DAEMON_PORT = port
                _EMBEDDING_BACKEND = "daemon"
                _register()
                return port
        logger.warning("another process's daemon did not start within %.1fs", _SPAWN_WAIT_S)
        _DAEMON_FAILED = True
        return None

    try:
        # Lock holder: reuse a live daemon if present, else spawn once.
        port = _reuse_existing_daemon()
        if port is not None:
            _DAEMON_PORT = port
            _EMBEDDING_BACKEND = "daemon"
            _register()
            return port

        # Retry daemon spawn up to 2 times
        for attempt in range(1, 3):
            port = _spawn_daemon()
            if port is not None:
                _DAEMON_PORT = port
                _EMBEDDING_BACKEND = "daemon"
                _register()
                return port
            logger.info("daemon spawn attempt %d/2 failed", attempt)

        logger.warning("daemon unavailable after 2 attempts — falling back to in-process model")
        _EMBEDDING_BACKEND = "in-process"
        _DAEMON_FAILED = True
        return None
    finally:
        _release_daemon_lock(lock)


def get_embedding_backend() -> str:
    """Return which backend answered embedding requests.

    "daemon" = shared embed daemon; "in-process" = MCP server's own
    SentenceTransformer (daemon unavailable); "unknown" = not yet determined.
    Pushed to the daemon so the dashboard can read it from one source.
    """
    return _EMBEDDING_BACKEND


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
            _push_backend()
    except httpx.RequestError as e:
        logger.warning("failed to register with daemon: %s", e)


def _push_backend() -> None:
    """Push the current embedding backend to the daemon (Q3=a)."""
    try:
        httpx.post(
            f"http://127.0.0.1:{_DAEMON_PORT}/api/backend",
            json={"backend": _EMBEDDING_BACKEND},
            timeout=3.0,
        )
    except httpx.RequestError:
        pass


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
                timeout=3.0,
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
    # F6: dimension guard — a model swap or corrupted vector must not silently
    # truncate via zip() and yield a meaningless similarity.
    if len(v1) != len(v2):
        logger.warning("embedding dimension mismatch: %d vs %d", len(v1), len(v2))
        return 0.0
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product(v1, v2) / (mag1 * mag2)


def load_precomputed_embeddings() -> Dict[str, List[float]]:
    """Load pre-computed embeddings (id -> vector) from the bundled JSONL file.

    The reserved ``_META_KEY`` entry (hashes) is excluded from the returned map.
    """
    vectors: Dict[str, List[float]] = {}
    try:
        if _EMBEDDINGS_FILE.is_file():
            with open(_EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    for key, value in entry.items():
                        if key == _META_KEY or not isinstance(value, list):
                            continue
                        if EXPECTED_DIM and len(value) != EXPECTED_DIM:
                            logger.warning(
                                "embedding for %s has dim %d (expected %d) — ignored",
                                key, len(value), EXPECTED_DIM,
                            )
                            continue
                        vectors[key] = value
    except Exception as e:
        logger.error(f"Failed to load pre-computed embeddings: {e}")
    return vectors


def load_embedding_hashes() -> Dict[str, str]:
    """Load content hashes (id -> hash) used for staleness detection (F2)."""
    try:
        if _EMBEDDINGS_FILE.is_file():
            with open(_EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if _META_KEY in entry:
                        meta = entry[_META_KEY]
                        if isinstance(meta, dict):
                            hashes = meta.get("hashes")
                            if isinstance(hashes, dict):
                                return {str(k): str(v) for k, v in hashes.items()}
    except Exception:
        pass
    return {}


def save_embeddings(embeddings: Dict[str, List[float]], hashes: Dict[str, str] | None = None) -> bool:
    """Atomically persist embeddings (+ optional hashes) as JSONL (F2/F5)."""
    try:
        tmp = _EMBEDDINGS_FILE.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            if hashes:
                f.write(json.dumps({_META_KEY: {"version": 1, "hashes": hashes}}) + "\n")
            for key, value in embeddings.items():
                f.write(json.dumps({key: value}) + "\n")
        os.replace(tmp, _EMBEDDINGS_FILE)
        return True
    except Exception as e:
        logger.warning("Failed to persist embeddings: %s", e)
        return False


def embed_text_for_entry(title: str, description: str, content: str) -> str:
    """Canonical 'passage:' document text for an entry (F4).

    Must match the generator (scripts/generate-catalog-embeddings.py) exactly so
    content hashes stay comparable across regenerations.
    """
    return f"passage: Title: {title}\nDescription: {description}\nContent: {content[:1000]}"


def hash_text(text: str) -> str:
    """Short stable hash of an embedding's source text (F2)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
