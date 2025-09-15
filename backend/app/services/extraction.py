import fitz  # PyMuPDF


def extract_text_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    text = "".join(page.get_text() for page in doc)
    return text


def textract_ocr(data: bytes) -> str:  # pragma: no cover - stub
    """TODO: integrate AWS Textract OCR"""
    raise NotImplementedError
