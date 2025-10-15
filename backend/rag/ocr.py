# backend/rag/ocr.py
from pathlib import Path
import os
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract

# Read env config
POPPLER_PATH = os.getenv("POPPLER_PATH") or None
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or None
OCR_DPI = int(os.getenv("OCR_DPI") or "300")
OCR_LANG = os.getenv("OCR_LANG") or "eng"

# On Windows you must set this
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def read_pdf_text(path: Path, max_pages: int = 300) -> str:
    """Extract text from native PDFs (has selectable text)."""
    reader = PdfReader(str(path))
    out = []
    for page in reader.pages[:max_pages]:
        try:
            out.append(page.extract_text() or "")
        except Exception:
            out.append("")
    return "\n".join(out)

def ocr_pdf_to_text(path: Path, max_pages: int = 300) -> str:
    """OCR for scanned PDFs: render pages to images with Poppler, then Tesseract."""
    kwargs = {"dpi": OCR_DPI}
    # pdf2image wants poppler_path on Windows
    if POPPLER_PATH:
        kwargs["poppler_path"] = POPPLER_PATH

    images = convert_from_path(str(path), **kwargs)
    texts = []
    for img in images[:max_pages]:
        try:
            txt = pytesseract.image_to_string(img, lang=OCR_LANG) or ""
        except Exception:
            txt = ""
        texts.append(txt)
    return "\n".join(texts)

def smart_pdf_extract(path: Path, max_pages: int = 300) -> tuple[str, dict]:
    """
    Try native text first; if too short (or empty), fall back to OCR.
    Return (text, metadata).
    """
    meta = {"path": str(path), "used_ocr": False, "dpi": OCR_DPI, "lang": OCR_LANG}
    native = read_pdf_text(path, max_pages=max_pages)
    # If native text is too small (typical for scanned PDFs), OCR it
    if len(native.strip()) >= 200:
        return native, meta
    ocr = ocr_pdf_to_text(path, max_pages=max_pages)
    meta["used_ocr"] = True
    return ocr, meta
