import json
import logging
import math
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent-guidance-mcp.embeddings")

_model = None
_model_lock = threading.Lock()

_E5_MODEL = "intfloat/multilingual-e5-small"

def get_embedding_model() -> Optional[Any]:
    global _model
    with _model_lock:
        if _model is not None:
            return _model

        try:
            import os
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
    """Pre-download the embedding model so server start doesn't trigger a download.

    Returns True if the model is available after this call.
    """
    model = get_embedding_model()
    return model is not None

_E5_QUERY_PREFIX = "query: "
_E5_PASSAGE_PREFIX = "passage: "

def get_embedding(text: str, prefix: str | None = None) -> Optional[List[float]]:
    """Generate a normalized embedding vector for the text using the local model.

    For E5 models, use prefix='query' for search queries and prefix='passage'
    for document/skill content to follow the asymmetric encoding convention.
    """
    model = get_embedding_model()
    if model is None:
        return None
    try:
        if prefix == "query":
            text = _E5_QUERY_PREFIX + text
        elif prefix == "passage":
            text = _E5_PASSAGE_PREFIX + text
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return None

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
