from pathlib import Path
from typing import List, Dict, Any, Iterable
from rag.ocr import smart_pdf_extract
from rag.chunker import chunk_text
from rag.embedder import embed_texts
from rag.store_chroma import get_collection
from rapidfuzz import fuzz
from datetime import datetime
import csv, os, hashlib, re, numpy as np

MIN_FUZZ = 50

# ---------- Helpers ----------
def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def _file_fingerprint(p: Path) -> str:
    """Stable-ish fingerprint: path + mtime + size -> sha1[:12]."""
    try:
        st = p.stat()
        basis = f"{str(p)}:{int(st.st_mtime)}:{st.st_size}"
    except Exception:
        basis = str(p)
    return _sha1(basis)[:12]

def _safe_row_key(row: Dict[str, Any], fallback: str) -> str:
    # Prefer a stable business key if present
    for k in ("record_id", "id", "reference_id"):
        v = (row.get(k) or "").strip()
        if v:
            return v
    return fallback

def _assemble_text(row: Dict[str, Any], text_fields: Iterable[str]) -> str:
    parts: List[str] = []
    for k in text_fields:
        v = (row.get(k) or "").strip()
        if v:
            # keep field labels to help lexical match
            parts.append(f"{k}: {v}")
    if parts:
        return "\n".join(parts)
    # last resort: concatenate any non-empty fields
    fallback = " ".join([str(v).strip() for v in row.values() if str(v).strip()])
    return fallback

def _label_prefix(meta: Dict[str, Any]) -> str:
    src = (meta.get("source_type") or meta.get("source") or "").upper() or "DOC"
    name = meta.get("file_name") or meta.get("csv_file") or ""
    return f"[{src} - {name}] "

def _cos(a, b):
    a = np.array(a); b = np.array(b)
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    return float(a @ b) / (na * nb + 1e-9)

def _tok(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (s or "").lower())

def _tfidf_scores(query: str, docs: List[str]) -> List[float]:
    # tiny TF-IDF cosine for rerank (no sklearn dep)
    from collections import Counter
    qtok = _tok(query)
    d_toks = [_tok(d) for d in docs]
    df = Counter()
    for toks in d_toks:
        for w in set(toks):
            df[w] += 1
    N = max(1, len(docs))

    keys = list(set(qtok) | set().union(*[set(t) for t in d_toks]))
    idx = {w: i for i, w in enumerate(keys)}

    def vec_from(toks):
        c = Counter(toks)
        v = np.zeros(len(keys))
        denom = max(1, len(toks))
        for w, ct in c.items():
            idf = np.log((N + 1) / (1 + df[w])) + 1.0
            v[idx[w]] = (ct / denom) * idf
        return v

    qv = vec_from(qtok); qn = np.linalg.norm(qv) + 1e-9
    dvs = [vec_from(t) for t in d_toks]
    return [float(qv @ dv) / (qn * (np.linalg.norm(dv) + 1e-9)) for dv in dvs]

def _mmr(candidates: List[int], qvec, emb_list: List[List[float]], k=5, lam=0.65):
    chosen = []
    cand = set(candidates)
    while cand and len(chosen) < k:
        best, best_i = -1e9, None
        for i in list(cand):
            sim_q = _cos(qvec, emb_list[i])
            div = 0.0 if not chosen else max(_cos(emb_list[i], emb_list[j]) for j in chosen)
            score = lam * sim_q - (1 - lam) * div
            if score > best:
                best, best_i = score, i
        chosen.append(best_i)
        cand.remove(best_i)
    return chosen



# ---------- TXT ingestion ----------
def ingest_txt_file(path: Path, delete_previous_for_same_file: bool = False) -> int:
    col = get_collection()
    if not path.exists():
        return 0
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = path.read_text(encoding="latin-1", errors="ignore")
    if not (text or "").strip():
        return 0

    file_fp = _file_fingerprint(path)
    if delete_previous_for_same_file:
        try:
            col.delete(where={"source": "txt", "file_fingerprint": file_fp})
        except Exception:
            pass

    chunks = chunk_text(text)
    ids = [f"txt::{file_fp}::{i}" for i, _ in enumerate(chunks)]
    metas = [{
        "source": "txt",
        "file_name": path.name,
        "path": str(path),
        "file_fingerprint": file_fp,
    } for _ in chunks]
    vecs = embed_texts(chunks)
    col.upsert(documents=chunks, embeddings=vecs, metadatas=metas, ids=ids)
    return len(ids)

# ---------- DOCX ingestion ----------
def ingest_docx_file(path: Path, delete_previous_for_same_file: bool = False) -> int:
    from docx import Document  # python-docx
    col = get_collection()
    if not path.exists():
        return 0
    try:
        doc = Document(str(path))
        paras = [p.text for p in doc.paragraphs]
        text = "\n\n".join([t for t in paras if t and t.strip()])
    except Exception:
        text = ""

    if not (text or "").strip():
        return 0

    file_fp = _file_fingerprint(path)
    if delete_previous_for_same_file:
        try:
            col.delete(where={"source": "docx", "file_fingerprint": file_fp})
        except Exception:
            pass

    chunks = chunk_text(text)
    ids = [f"docx::{file_fp}::{i}" for i, _ in enumerate(chunks)]
    metas = [{
        "source": "docx",
        "file_name": path.name,
        "path": str(path),
        "file_fingerprint": file_fp,
    } for _ in chunks]
    vecs = embed_texts(chunks)
    col.upsert(documents=chunks, embeddings=vecs, metadatas=metas, ids=ids)
    return len(ids)
# ---------- PDF ingestion ----------
def ingest_pdf_dir(pdf_dir: Path, max_files: int = 100, delete_previous_for_same_file: bool = False) -> int:
    col = get_collection()
    paths = list(pdf_dir.glob("*.pdf"))[:max_files]
    total = 0
    for path in paths:
        text, meta = smart_pdf_extract(path)  # meta may include source_type=pdf or pdf_ocr
        if not (text or "").strip():
            continue

        file_fp = _file_fingerprint(path)
        if delete_previous_for_same_file:
            try:
                col.delete(where={"source": "pdf", "file_fingerprint": file_fp})
                col.delete(where={"source": "pdf_ocr", "file_fingerprint": file_fp})
            except Exception:
                pass

        docs, metas, ids = [], [], []
        # ensure we have a clear source_type for labeling
        source_type = meta.get("source_type") or "pdf"
        for i, ch in enumerate(chunk_text(text)):
            label = _label_prefix({"source_type": source_type, "file_name": path.name})
            chunk_for_store = label + ch
            docs.append(chunk_for_store)
            metas.append({
                "source": source_type,                 # keep simple: "pdf" or "pdf_ocr"
                "source_type": source_type,
                "file_name": path.name,
                "file_fingerprint": file_fp,
                "chunk": i,
                **meta,
                "ingested_at": datetime.utcnow().isoformat() + "Z",
            })
            cid = _sha1(f"pdf:{file_fp}:{source_type}:{i}:{len(ch)}")[:10]
            ids.append(f"pdf:{file_fp}:{source_type}:c{i}:{cid}")

        if docs:
            vecs = embed_texts(docs)
            col.upsert(documents=docs, embeddings=vecs, metadatas=metas, ids=ids)
            total += len(ids)
    return total

def ingest_pdf_file(path: Path, delete_previous_for_same_file: bool = False) -> int:
    """
    Ingest a single PDF file (mirror of ingest_pdf_dir loop body).
    Returns number of chunks added.
    """
    col = get_collection()
    if not path.exists():
        return 0

    text, meta = smart_pdf_extract(path)  # meta may include source='pdf' or 'pdf_ocr'
    if not (text or "").strip():
        return 0

    # same fingerprinting/cleanup used in ingest_pdf_dir
    file_fp = _file_fingerprint(path)
    if delete_previous_for_same_file:
        try:
            col.delete(where={"source": "pdf", "file_fingerprint": file_fp})
            col.delete(where={"source": "pdf_ocr", "file_fingerprint": file_fp})
        except Exception:
            pass

    chunks = chunk_text(text)
    ids = [f"pdf::{file_fp}::{i}" for i, _ in enumerate(chunks)]
    metas = []
    for i, ch in enumerate(chunks):
        m: Dict[str, Any] = {
            "source": meta.get("source", "pdf"),  # e.g., "pdf" or "pdf_ocr"
            "file_name": path.name,
            "path": str(path),
            "file_fingerprint": file_fp,
            "chunk": i,
            "chunk_char_count": len(ch),
            "ingested_at": datetime.utcnow().isoformat() + "Z",
        }
        metas.append(m)

    vecs = embed_texts(chunks)
    col.upsert(documents=chunks, embeddings=vecs, metadatas=metas, ids=ids)
    return len(ids)


# ---------- CSV ingestion ----------
def ingest_csv_file(csv_path: Path, delete_previous_for_same_file: bool = True) -> int:
    """
    - Unique, deterministic IDs per row+chunk.
    - Accepts both your CSV (title/body/description/content) and 'summary' (demo CSV).
    - Stores file_fingerprint; prefixes chunks with a label to help lexical retrieval.
    """
    col = get_collection()
    file_fp = _file_fingerprint(csv_path)

    if delete_previous_for_same_file:
        try:
            col.delete(where={"source": "csv", "file_fingerprint": file_fp})
        except Exception:
            pass

    text_fields = ("title", "body", "description", "content", "summary")
    metadata_fields = (
        "record_id", "id", "reference_id", "jurisdiction", "category",
        "risk_level", "doc_type", "compliance_owner",
        "effective_date", "last_updated", "source_url", "section", "keywords",
    )

    docs: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []

    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=1):
            body = _assemble_text(row, text_fields).strip()
            if not body:
                continue

            chunks = list(chunk_text(body))
            if not chunks:
                continue

            row_key = _safe_row_key(row, fallback=f"row-{row_idx}")

            base_meta: Dict[str, Any] = {
                "source": "csv",
                "source_type": "csv",
                "csv_file": csv_path.name,
                "file_fingerprint": file_fp,
                "row_index": row_idx,
                "ingested_at": datetime.utcnow().isoformat() + "Z",
            }
            for mf in metadata_fields:
                if mf in row and row[mf] is not None and str(row[mf]).strip():
                    base_meta[mf] = str(row[mf]).strip()

            for c_idx, ch in enumerate(chunks):
                label = _label_prefix(base_meta)
                chunk_for_store = label + ch
                docs.append(chunk_for_store)
                m = dict(base_meta)
                m["chunk"] = c_idx
                m["chunk_char_count"] = len(ch)
                metas.append(m)
                h = _sha1(f"csv:{file_fp}:{row_key}:{c_idx}:{len(ch)}")[:10]
                ids.append(f"csv:{file_fp}:{row_key}:c{c_idx}:{h}")

    if not docs:
        return 0

    vecs = embed_texts(docs)
    col.upsert(documents=docs, embeddings=vecs, metadatas=metas, ids=ids)
    return len(ids)

# ---------- Retrieval ----------
def _expand_query(q: str) -> List[str]:
    """Domain expansions to help loose questions match."""
    CANON = {
        r"\bkyc\b": ["know your customer", "customer due diligence", "e-kyc", "identity verification"],
        r"\baml\b": ["anti-money laundering", "money laundering controls"],
        r"\bpep\b": ["politically exposed person", "pep screening"],
        r"\bgdpr\b": ["data protection", "privacy regulation"],
        r"\bcross[- ]?border\b": ["international", "overseas transfer", "x-border"],
        r"\bbiometric\b": ["face id", "fingerprint", "e-kyc"],
        r"\bdigital banking\b": ["online banking", "fintech"],
        r"\bdbsr\b": ["digital banking supervision regulation", "eu digital regulation"],
    }
    terms = [q.strip()]
    low = q.lower()
    for pat, alts in CANON.items():
        if re.search(pat, low):
            terms.extend(alts)
    if "effective" in low or "when" in low:
        terms.append("effective date")
    if "risk" in low:
        terms.append("risk level")
    # unique, preserve order
    out, seen = [], set()
    for t in terms:
        if t and t not in seen:
            out.append(t); seen.add(t)
    return out[:3]

def retrieve_topk(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval:
      - Build a big candidate pool from multiple query variants (vectors).
      - Rerank using vector sim + TF-IDF + fuzzy, with small domain boosts.
      - Apply MMR for diversity.
    """
    col = get_collection()
    q = re.sub(r"\s+", " ", (query or "").strip())
    variants = _expand_query(q)
    qvecs = embed_texts(variants)

    pool = max(top_k * 6, 30)
    agg_docs, agg_metas, agg_ids, agg_embs = [], [], [], []
    seen = set()

    for vvec in qvecs:
        res = col.query(
            query_embeddings=[vvec],
            n_results=pool,
            include=["embeddings", "documents", "metadatas"]  # ✅
        )
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        ids = res.get("ids", [[]])[0]
        embs = res.get("embeddings", [[]])[0]
        for d, m, i, e in zip(docs, metas, ids, embs):
            if i in seen:
                continue
            seen.add(i)
            agg_docs.append(d); agg_metas.append(m); agg_ids.append(i); agg_embs.append(e)

    if not agg_docs:
        return []

    # Scores: vector (vs base query), tf-idf, fuzzy
    base_qvec = qvecs[0]
    vec_scores  = np.array([_cos(base_qvec, e) for e in agg_embs])
    tfidf_sc    = np.array(_tfidf_scores(q, agg_docs))
    fuzzy_sc    = np.array([fuzz.token_set_ratio(q, d) / 100.0 for d in agg_docs])

    # Domain-aware tiny boosts to help OCR/metadata hits
    boosts = np.zeros(len(agg_docs))
    low = q.lower()
    for i, m in enumerate(agg_metas):
        st = (m.get("source_type") or m.get("source") or "").lower()
        if "ocr" in st:
            boosts[i] += 0.04            # ensure OCR chunks aren’t drowned out
        if "singapore" in low and str(m.get("jurisdiction","")).lower() == "singapore":
            boosts[i] += 0.05
        if "risk" in low and str(m.get("risk_level","")).lower() == "high":
            boosts[i] += 0.05

    score = 0.55 * vec_scores + 0.25 * tfidf_sc + 0.20 * fuzzy_sc + boosts

    # Take topN and diversify
    topN = np.argsort(-score)[:max(5 * top_k, 30)].tolist()
    chosen = _mmr(topN, base_qvec, agg_embs, k=top_k, lam=0.65)

    return [{"id": agg_ids[i], "text": agg_docs[i], "meta": agg_metas[i], "score": float(score[i])} for i in chosen]
