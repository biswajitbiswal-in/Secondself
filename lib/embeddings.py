"""
sentence-transformers wrapper for SecondSelf.

Provides:
  - load_model(): Cached loading of all-MiniLM-L6-v2
  - embed_text(text): Return 384-dim numpy vector
  - cosine_similarity(a, b): Similarity score
  - load_embeddings() / save_embeddings(): Persist to data/embeddings.pkl
"""

import logging
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import config

logger = logging.getLogger(__name__)

# Singleton model reference
_MODEL = None


def load_model():
    """
    Load the sentence-transformers model (cached singleton).

    Uses the model name from config.EMBEDDING_MODEL (default: all-MiniLM-L6-v2).
    The model is cached on first load for subsequent calls.

    Returns:
        SentenceTransformer model instance.
    """
    global _MODEL
    if _MODEL is None:
        logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully.")
    return _MODEL


def embed_text(text: str) -> np.ndarray:
    """
    Embed a text string into a 384-dimensional vector.

    Args:
        text: The text to embed.

    Returns:
        numpy array of shape (384,) containing the embedding vector.
        Returns zero vector on failure.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for embedding, returning zero vector.")
        return np.zeros(384, dtype=np.float32)

    try:
        model = load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return np.zeros(384, dtype=np.float32)


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Embed multiple texts at once (more efficient than calling embed_text in a loop).

    Args:
        texts: List of text strings to embed.

    Returns:
        numpy array of shape (len(texts), 384) containing embedding vectors.
    """
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)

    try:
        model = load_model()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(embeddings, dtype=np.float32)
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        return np.zeros((len(texts), 384), dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a: First vector (numpy array).
        b: Second vector (numpy array).

    Returns:
        Cosine similarity score (0.0 to 1.0).
    """
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if b.ndim == 1:
        b = b.reshape(1, -1)

    # Normalize if not already normalized
    a_norm = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-10)

    return float(np.dot(a_norm, b_norm.T).flatten()[0])


def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Compute the full pairwise cosine similarity matrix.

    Args:
        embeddings: numpy array of shape (N, 384).

    Returns:
        numpy array of shape (N, N) with cosine similarities.
    """
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=-1, keepdims=True) + 1e-10
    normalized = embeddings / norms
    return np.dot(normalized, normalized.T)


# ---------------------------------------------------------------------------
# Persistence (data/embeddings.pkl)
# ---------------------------------------------------------------------------

EMBEDDINGS_PATH = config.BASE_DIR / "data" / "embeddings.pkl"


def get_text_for_embedding(note) -> str:
    """
    Build the text string to embed from a wiki note.

    Combines summary + body for a rich semantic representation.

    Args:
        note: WikiNote object (or any object with summary and body attributes).

    Returns:
        Concatenated text string.
    """
    parts = []
    if note.summary:
        parts.append(note.summary)
    if note.body:
        # Use first 2000 chars of body to keep embeddings focused
        body_preview = note.body[:2000]
        parts.append(body_preview)
    return "\n\n".join(parts)


def text_hash(text: str) -> str:
    """Hash text to detect changes for re-embedding."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_embeddings(embeddings_dict: Dict[str, dict]):
    """
    Save embeddings dictionary to data/embeddings.pkl.

    Structure:
    {
        note_id: {
            "embedding": np.ndarray (384,),
            "text_hash": str,
            "note_id": str,
        },
        ...
    }

    Args:
        embeddings_dict: Dictionary mapping note_id to embedding data.
    """
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(EMBEDDINGS_PATH, "wb") as f:
            pickle.dump(embeddings_dict, f)
        logger.debug(f"Saved {len(embeddings_dict)} embeddings to {EMBEDDINGS_PATH}")
    except Exception as e:
        logger.error(f"Failed to save embeddings: {e}")


def load_embeddings() -> Dict[str, dict]:
    """
    Load embeddings dictionary from data/embeddings.pkl.

    Returns:
        Dictionary mapping note_id to embedding data, or empty dict if file missing.
    """
    if not EMBEDDINGS_PATH.exists():
        logger.debug("No embeddings file found, starting fresh.")
        return {}

    try:
        with open(EMBEDDINGS_PATH, "rb") as f:
            embeddings_dict = pickle.load(f)
        logger.debug(f"Loaded {len(embeddings_dict)} embeddings from {EMBEDDINGS_PATH}")
        return embeddings_dict
    except Exception as e:
        logger.warning(f"Failed to load embeddings from {EMBEDDINGS_PATH}: {e}")
        return {}


def get_embedding_vector(note_id: str) -> Optional[np.ndarray]:
    """
    Get the embedding vector for a specific note ID.

    Args:
        note_id: The wiki note ID.

    Returns:
        numpy array of shape (384,) or None if not found.
    """
    embeddings_dict = load_embeddings()
    entry = embeddings_dict.get(note_id)
    if entry is not None and "embedding" in entry:
        return entry["embedding"]
    return None


def get_all_embedding_vectors() -> Tuple[List[str], np.ndarray]:
    """
    Get all note IDs and their embedding vectors as a matrix.

    Returns:
        Tuple of (note_ids list, embedding_matrix of shape (N, 384)).
        Returns empty list and (0, 384) matrix if no embeddings exist.
    """
    embeddings_dict = load_embeddings()
    if not embeddings_dict:
        return [], np.zeros((0, 384), dtype=np.float32)

    note_ids = []
    vectors = []
    for note_id, data in embeddings_dict.items():
        if "embedding" in data:
            note_ids.append(note_id)
            vectors.append(data["embedding"])

    if not vectors:
        return [], np.zeros((0, 384), dtype=np.float32)

    return note_ids, np.array(vectors, dtype=np.float32)

