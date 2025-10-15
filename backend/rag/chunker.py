from typing import List

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        start += size - overlap
    return [c for c in chunks if c.strip()]
