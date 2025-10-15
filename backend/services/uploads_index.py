# backend/services/uploads_index.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from core.settings import settings

DATA_DIR = Path(settings.DATA_DIR)
INDEX_PATH = DATA_DIR / "uploads.json"
INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

def _load() -> List[Dict[str, Any]]:
    if not INDEX_PATH.exists():
        return []
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save(rows: List[Dict[str, Any]]) -> None:
    INDEX_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

def list_uploads() -> List[Dict[str, Any]]:
    rows = _load()
    rows.sort(key=lambda r: r.get("created_at",""), reverse=True)
    return rows

def add_upload(entry: Dict[str, Any]) -> None:
    rows = _load()
    rows.append(entry)
    _save(rows)

def get_upload(upload_id: str) -> Optional[Dict[str, Any]]:
    for r in _load():
        if r.get("id") == upload_id:
            return r
    return None

def remove_upload(upload_id: str) -> bool:
    rows = _load()
    new_rows = [r for r in rows if r.get("id") != upload_id]
    if len(new_rows) == len(rows):
        return False
    _save(new_rows)
    return True

def mark_ingested(upload_id: str, *, chunk_count: int, error: Optional[str]=None) -> None:
    rows = _load()
    changed = False
    for r in rows:
        if r.get("id") == upload_id:
            r["ingested"] = error is None
            r["error"] = error
            r["chunk_count"] = int(chunk_count)
            r["updated_at"] = datetime.utcnow().isoformat() + "Z"
            changed = True
            break
    if changed:
        _save(rows)
