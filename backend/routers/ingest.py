from fastapi import APIRouter, UploadFile, File, Depends
from pathlib import Path
from core.auth import bearer_auth
from core.models import IngestResponse
from core.settings import settings
from rag.retriever import ingest_pdf_dir, ingest_csv_file, ingest_docx_file, ingest_txt_file
# from rag.ingest_csv import ingest_csv_file
from fastapi import Query
from uuid import uuid4
from datetime import datetime
from services import uploads_index
from rag.retriever import ingest_pdf_file
from rag.retriever import _sha1
from rag.retriever import _file_fingerprint

router = APIRouter(tags=["ingest"])

DATA_DIR = Path(settings.DATA_DIR)
PDF_DIR = DATA_DIR / "pdfs"
CSV_DIR = DATA_DIR / "csv"
DOCX_DIR = DATA_DIR / "docx"
TXT_DIR = DATA_DIR / "txt"
PDF_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)
DOCX_DIR.mkdir(parents=True, exist_ok=True)
TXT_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)

# backend/routers/ingest.py

# @router.get("/debug/ocr")
# def debug_ocr(sample: str = Query(..., description="Path to a PDF on server disk"),
#               _ok: bool = Depends(bearer_auth)):
#     """
#     Quick OCR test to verify Poppler/Tesseract integration on a single PDF file path.
#     Example: /api/debug/ocr?sample=./data/pdfs/scanned_notice.pdf
#     """
#     from rag.ocr import smart_pdf_extract
#     from pathlib import Path as _P
#     p = _P(sample)
#     if not p.exists():
#         return {"error": f"File not found: {sample}"}
#     text, meta = smart_pdf_extract(p)
#     return {"len": len(text), "preview": text[:400], "meta": meta}

# @router.get("/debug/index")
# def debug_index(_ok: bool = Depends(bearer_auth)):
#     from rag.store_chroma import get_collection
#     col = get_collection()

#     try:
#         total = col.count()  # quick total doc count
#         # fetch a small sample (ids are ALWAYS returned; don't request them in include)
#         res = col.get(limit=5, include=["documents", "metadatas"])  # ✅ no "ids" in include
#         return {
#             "count": total,
#             "sample_ids": res.get("ids", [])[:5],          # ids come regardless of include
#             "sample_meta": res.get("metadatas", [])[:3],
#         }
#     except Exception as e:
#         return {"error": str(e)}
    
# @router.post("/ingest/pdf", response_model=IngestResponse)
# async def ingest_pdf(file: UploadFile = File(...), _ok: bool = Depends(bearer_auth)):
#     target = PDF_DIR / file.filename
#     with open(target, "wb") as f:
#         f.write(await file.read())
#     chunks = ingest_pdf_dir(PDF_DIR)
#     return {"chunks_ingested": chunks, "files": 1}

# @router.post("/ingest/csv")
# async def ingest_csv(file: UploadFile = File(...), _ok: bool = Depends(bearer_auth)):
#     dest = CSV_DIR / file.filename
#     dest.write_bytes(await file.read())
#     count = ingest_csv_file(dest)
#     return {"file": str(dest), "rows_ingested": count}


@router.post("/upload")
async def ingest_upload(file: UploadFile = File(...), auth=Depends(bearer_auth)):
    name = (file.filename or "").lower()
    content = await file.read()

    _id = str(uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    def index_and_return(file_type: str, path: Path, added: int):
        """Helper: register upload, mark ingested, return response"""
        stat = path.stat()
        file_fp = _file_fingerprint(path)

        uploads_index.add_upload({
            "id": _id,
            "original_filename": name,
            "stored_path": str(path),
            "size_bytes": int(stat.st_size),
            "created_at": now,
            "ingested": False,
            "error": None,
            "chunk_count": 0,
            "file_type": file_type,
            "file_fingerprint": file_fp,
        })

        uploads_index.mark_ingested(_id, chunk_count=int(added), error=None)
        return {"type": file_type, "file": name, "chunks": added}

    # ---------- PDF ----------
    if name.endswith(".pdf") or file.content_type == "application/pdf":
        path = PDF_DIR / name
        path.write_bytes(content)
        try:
            added = ingest_pdf_file(path, delete_previous_for_same_file=True)
            return index_and_return("pdf", path, added)
        except Exception as e:
            uploads_index.mark_ingested(_id, chunk_count=0, error=str(e))
            raise

    # ---------- CSV ----------
    elif name.endswith(".csv") or "csv" in (file.content_type or ""):
        path = CSV_DIR / name
        path.write_bytes(content)
        try:
            added = ingest_csv_file(path, delete_previous_for_same_file=True)
            return index_and_return("csv", path, added)
        except Exception as e:
            uploads_index.mark_ingested(_id, chunk_count=0, error=str(e))
            raise

    # ---------- TXT ----------
    elif name.endswith(".txt") or file.content_type in ("text/plain",):
        path = TXT_DIR / name
        path.write_bytes(content)
        try:
            added = ingest_txt_file(path, delete_previous_for_same_file=True)
            return index_and_return("txt", path, added)
        except Exception as e:
            uploads_index.mark_ingested(_id, chunk_count=0, error=str(e))
            raise

    # ---------- DOCX ----------
    elif name.endswith(".docx") or file.content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        path = DOCX_DIR / name
        path.write_bytes(content)
        try:
            added = ingest_docx_file(path, delete_previous_for_same_file=True)
            return index_and_return("docx", path, added)
        except Exception as e:
            uploads_index.mark_ingested(_id, chunk_count=0, error=str(e))
            raise

    # ---------- Unsupported ----------
    else:
        return {"error": f"Unsupported file type: {file.content_type} / {name}"}
