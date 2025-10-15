# backend/agent/tools.py
from typing import List, Dict, Any
from backend.rag.retriever import retrieve_topk
import csv
from pathlib import Path
from backend.core.settings import settings

def retrieve_documents(query: str, top_k: int = 6) -> Dict[str, Any]:
    """RAG fetch: return text + minimal meta for the agent to reason over."""
    hits = retrieve_topk(query, top_k=top_k)
    # Keep it compact
    return {
        "results": [
            {
                "text": h["text"],
                "source": h["meta"].get("path") or h["id"],
                "meta": h["meta"],
            }
            for h in hits
        ]
    }

def check_policy(rule: str) -> Dict[str, Any]:
    """
    A toy 'policy checker' over the CSV (e.g., key rotation).
    Looks into ./data/csv first CSV and returns matching rows.
    """
    data_dir = Path(settings.DATA_DIR)
    csv_files = list((data_dir / "csv").glob("*.csv"))
    if not csv_files:
        return {"matches": []}
    path = csv_files[0]
    matches = []
    with open(path, newline='', encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            text = " ".join([row.get("title",""), row.get("body",""), row.get("description",""), row.get("content","")])
            if rule.lower() in text.lower():
                matches.append({"id": row.get("id"), "title": row.get("title"), "body": row.get("body")})
    return {"matches": matches}
