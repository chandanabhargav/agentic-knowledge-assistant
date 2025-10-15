# backend/rag/query_utils.py
import re

CANON = {
    r"\bkyc\b": ["know your customer", "customer due diligence", "e-kyc", "identity verification"],
    r"\baml\b": ["anti-money laundering", "money laundering controls"],
    r"\bpep\b": ["politically exposed person", "pep screening"],
    r"\bgdpr\b": ["data protection", "privacy regulation"],
    r"\bcross[- ]?border\b": ["international", "x-border", "overseas transfer"],
    r"\bbiometric\b": ["face id", "fingerprint", "e-kyc"],
    r"\bdigital banking\b": ["online banking", "fintech"],
    r"\bdbsr\b": ["digital banking supervision regulation", "eu digital regulation"],
}

def normalize_query(q: str) -> str:
    q = re.sub(r"\s+", " ", q or "").strip()
    return q

def expand_query(q: str, max_terms: int = 8) -> list[str]:
    terms = [q]
    low = q.lower()
    for pat, alts in CANON.items():
        if re.search(pat, low):
            terms.extend(alts)
    # also add mild variants
    if "effective" in low or "when" in low:
        terms.append("effective date")
    if "risk" in low:
        terms.append("risk level")
    # unique, keep order
    seen, out = set(), []
    for t in terms:
        if t not in seen:
            out.append(t); seen.add(t)
    return out[:max_terms]
