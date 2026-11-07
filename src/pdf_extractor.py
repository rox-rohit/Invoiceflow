from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

@dataclass
class PDFPage:
    number: int
    text: str
    words: list[tuple]

@dataclass
class PDFDocument:
    path: Path
    pages: list[PDFPage]
    text: str
    is_scanned: bool
    page_count: int = 0

def extract_pdf(path: str | Path) -> PDFDocument:
    path = Path(path)
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise ValueError(f"Unable to open PDF: {exc}") from exc
    with doc:
        if doc.needs_pass:
            raise PermissionError("Password-protected PDF; enter the password or export an unlocked copy.")
        if len(doc) == 0:
            raise ValueError("PDF contains no pages.")
        pages = []
        chars = 0
        for index, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(PDFPage(index + 1, text, page.get_text("words")))
            chars += len(text.strip())
    return PDFDocument(path, pages, "\n".join(p.text for p in pages), chars < 20, len(pages))
