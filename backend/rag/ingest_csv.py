from pathlib import Path
from typing import List, Dict, Any, Optional
import csv

from backend.rag.store_chroma import get_collection
from backend.rag.embedder import embed_texts

# Accept multiple delimiters if Sniffer fails
CANDIDATE_DELIMS = [',', ';', '\t', '|']

def _row_to_text(row: Dict[str, Any]) -> str:
    parts = []
    for k, v in row.items():
        if v is None:
            v = ""
        v = str(v).strip()
        if v:
            parts.append(f"{k}: {v}")
    return "\n".join(parts).strip()

def _open_csv(path: Path):
    """
    Try utf-8-sig (handles Excel BOM), then utf-8, then latin-1 as last resort.
    Return (file_obj, sample_text)
    """
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            f = path.open("r", encoding=enc, newline="")
            sample = f.read(4096)
            f.seek(0)
            return f, sample
        except Exception:
            continue
    # fallback binary read
    f = path.open("r", errors="ignore", newline="")
    sample = f.read(4096); f.seek(0)
    return f, sample

def _dict_reader(path: Path) -> Optional[csv.DictReader]:
    f, sample = _open_csv(path)
    # Try to sniff dialect
    try:
        dialect = csv.Sniffer().sniff(sample)
        reader = csv.DictReader(f, dialect=dialect)
        # Ensure headers exist; if not, fall back
        if not reader.fieldnames or all(h is None or h.strip()=="" for h in reader.fieldnames):
            raise ValueError("Empty headers after sniffer")
        return reader
    except Exception:
        # Fallback over common delimiters
        f.close()
        for d in CANDIDATE_DELIMS:
            f2, _ = _open_csv(path)
            reader = csv.DictReader(f2, delimiter=d)
            if reader.fieldnames and any(h and h.strip() for h in reader.fieldnames):
                return reader
        return None

def ingest_csv_file(path: Path) -> int:
    """
    Turn each CSV row into a small text document and upsert.
    Returns number of rows ingested.
    """
    col = get_collection()

    # Idempotent: delete any prior docs for this file
    try:
        existing = col.get(where={"path": str(path)}, include=[])
        ex_ids = existing.get("ids", [])
        if ex_ids:
            col.delete(ids=ex_ids)
    except Exception:
        pass

    reader = _dict_reader(path)
    if reader is None:
        return 0

    docs: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []

    # Skip an empty first row if present
    for i, row in enumerate(reader):
        text = _row_to_text(row)
        # Remove aggressive length filters; index even short rows
        if not text:
            continue
        ids.append(f"csv::{path.name}::row{i}")
        metas.append({
            "source": "csv",
            "path": str(path),
            "row_index": i,
            "headers": list(reader.fieldnames or []),
        })
        docs.append(text)

    if not docs:
        return 0

    vecs = embed_texts(docs)
    col.upsert(documents=docs, embeddings=vecs, metadatas=metas, ids=ids)
    return len(ids)
