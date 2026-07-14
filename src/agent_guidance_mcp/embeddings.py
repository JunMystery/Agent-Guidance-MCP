import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent-guidance-mcp.embeddings")

_model = None

def get_embedding_model() -> Optional[Any]:
    """Lazy load the sentence-transformers model."""
    global _model
    if _model is not None:
        return _model
    
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers/all-MiniLM-L6-v2 model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
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

def get_embedding(text: str) -> Optional[List[float]]:
    """Generate a normalized embedding vector for the text using the local model."""
    model = get_embedding_model()
    if model is None:
        return None
    try:
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
