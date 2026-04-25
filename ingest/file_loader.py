"""Load text content from local files (.txt, .md, .pdf, .docx)."""
from pathlib import Path


def load_file(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    suffix = p.suffix.lower()

    if suffix in (".txt", ".md"):
        return p.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        return _load_pdf(p)

    if suffix == ".docx":
        return _load_docx(p)

    raise ValueError(f"Unsupported file type '{suffix}'. Supported: .txt .md .pdf .docx")


def _load_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for PDF support. Run: pip install pypdf")

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


def _load_docx(path: Path) -> str:
    try:
        import docx
    except ImportError:
        raise ImportError("python-docx is required for DOCX support. Run: pip install python-docx")

    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
