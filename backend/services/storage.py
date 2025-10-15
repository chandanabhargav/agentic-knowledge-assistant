# backend/services/storage.py
from pathlib import Path

def delete_local(path_str: str) -> None:
    try:
        p = Path(path_str)
        if p.exists():
            p.unlink()
    except Exception:
        # demo-grade: ignore failures
        pass
