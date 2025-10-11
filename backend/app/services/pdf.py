from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(pdf_bytes: bytes) -> str:
    buffer = BytesIO(pdf_bytes)
    reader = PdfReader(buffer)
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text.strip())
    return "\n\n".join(t for t in pages_text if t)
