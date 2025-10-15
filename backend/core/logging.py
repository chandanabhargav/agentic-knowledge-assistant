import json, time
from pathlib import Path

LOG_PATH = Path("./audit.log.jsonl")

def log_interaction(query: str, answer: str, citations):
    rec = {
        "ts": int(time.time()),
        "query": query,
        "answer_preview": answer[:200],
        "citations": citations,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
