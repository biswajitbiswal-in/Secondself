"""
Centralized Configuration for SecondSelf Personal AI Second Brain.
Defines storage paths, model names, similarity thresholds, and API keys.
"""

import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Data and Persistence Directories
RAW_DIR = BASE_DIR / "raw"
WIKI_DIR = BASE_DIR / "wiki"
EMBEDDINGS_DIR = BASE_DIR / "embeddings"
GRAPH_PATH = BASE_DIR / "graph.json"
TEMPLATES_DIR = BASE_DIR / "templates"

# PARA Categories
PARA_CATEGORIES = ["Projects", "Areas", "Resources", "Archives"]

# Model and Pipeline Constants
SIMILARITY_THRESHOLD = 0.75
TOP_K_RETRIEVAL = 5
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama3-8b-8192"
MAX_CONTENT_CHARS = 8000  # Character truncation limit for LLM processing

# API Keys & External Credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def ensure_directories_exist():
    """Ensure all required project directories exist."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    for category in PARA_CATEGORIES:
        (WIKI_DIR / category).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_directories_exist()
    print("Configuration loaded and directory structure verified.")
