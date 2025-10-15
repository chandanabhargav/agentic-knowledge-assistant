# backend/rag/store_chroma.py
from pathlib import Path
import chromadb
from chromadb.config import Settings
from core.settings import settings

# Ensure the directory exists (even if it's a mounted volume)
Path(settings.INDEX_DIR).mkdir(parents=True, exist_ok=True)

# Turn off telemetry (avoids edge crashes on some builds)
_client = chromadb.PersistentClient(
    path=settings.INDEX_DIR,
    settings=Settings(allow_reset=True, anonymized_telemetry=False),
)

COLLECTION = "rag_demo"

def get_collection():
    """
    Always return a valid collection.
    Works on first run, after resets, and across container restarts.
    """
    # Newer Chroma
    if hasattr(_client, "get_or_create_collection"):
        return _client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
    # Older fallback
    try:
        return _client.get_collection(COLLECTION)
    except Exception:
        return _client.create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
