# backend/routers/uploads.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from backend.core.auth import bearer_auth
from backend.services import uploads_index
from backend.rag.store_chroma import get_collection
from backend.services.storage import delete_local
from pathlib import Path

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.get("", dependencies=[Depends(bearer_auth)])
def list_uploads() -> List[Dict[str, Any]]:
    return uploads_index.list_uploads()

@router.delete("/{upload_id}", status_code=204, dependencies=[Depends(bearer_auth)])
def delete_upload(upload_id: str):
    # 1️⃣ Get the index entry
    row = uploads_index.get_upload(upload_id)
    print(row)
    if not row:
        raise HTTPException(status_code=404, detail="Upload not found")

    file_path = row.get("stored_path")
    file_fp   = row.get("file_fingerprint")
    print(file_path, "file_path")
    print(file_fp, "file_fp")

    # 2️⃣ Delete the physical file first (folder)
    if file_path:
        try:
            p = Path(file_path)
            print(p.exists(), "p.exists()")
            if p.exists():
                p.unlink()  # remove the file
        except Exception as e:
            # non-fatal — log if needed
            print(f"[delete_upload] Failed to delete file {file_path}: {e}")

    # 3️⃣ Remove from uploads.json index
    uploads_index.remove_upload(upload_id)

    # 4️⃣ Delete vectors for this file (by fingerprint if available)
    try:
        col = get_collection()
        sample_result = col.get(limit=1, include=['metadatas'])

        if sample_result and sample_result.get('metadatas'):
            print("\n--- INGESTION METADATA SCHEMA ---")
            print(sample_result['metadatas'][0])
            print("---------------------------------")

        def get_ids(where: dict) -> list[str]:
            # include=[] avoids pulling embeddings/docs; Chroma always returns 'ids'
            res = col.get(where=where, include=[])
            return res.get("ids", []) or []

        # Build progressively wider queries
        fp   = row.get("file_fingerprint")
        name = row.get("original_filename")
        path = row.get("stored_path")
        src  = row.get("file_type")  # "pdf" | "csv" | "txt" | "docx" | etc.

        candidate_ids: list[str] = []

        # 1) Best: by fingerprint
        if fp:
            ids = get_ids({"file_fingerprint": fp})
            print("ids by fingerprint:", len(ids))
            candidate_ids.extend(ids)

        # 2) Fallback: by full path (+source if available)
        if not candidate_ids and path:
            filt = {"path": path}
            if src:
                filt["source"] = src
            ids = get_ids(filt)
            print("ids by path/src:", len(ids), filt)
            candidate_ids.extend(ids)

        # 3) Fallback: by file_name (+source)
        if not candidate_ids and name:
            filt = {"file_name": name}
            if src:
                filt["source"] = src
            ids = get_ids(filt)
            print("ids by file_name/src:", len(ids), filt)
            candidate_ids.extend(ids)

        # dedupe while preserving order
        candidate_ids = list(dict.fromkeys(candidate_ids))
        print("total ids to delete:", len(candidate_ids))

        if candidate_ids:
            col.delete(ids=candidate_ids)
            # verify
            remaining = col.get(ids=candidate_ids, include=[])
            still_there = len(remaining.get("ids", []) or [])
            print("deleted, still_there:", still_there)
        else:
            print("⚠️ No matching vectors found for this upload. Check metadata stored during ingest.")

    except Exception as e:
        print(f"[delete_upload] Vector delete error for {row.get('stored_path')}: {e}")