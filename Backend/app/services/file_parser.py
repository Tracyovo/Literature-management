from __future__ import annotations

from pathlib import Path

import chardet
import pdfplumber
from docx import Document


def extract_text_from_pdf(path: Path) -> str:
    content: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text:
                content.append(text)
    return "\n".join(content)


def extract_text_from_docx(path: Path) -> str:
    document = Document(path)
    return "\n".join(para.text for para in document.paragraphs if para.text)


def extract_text_from_txt(path: Path) -> str:
    data = path.read_bytes()
    encoding = chardet.detect(data).get("encoding") or "utf-8"
    return data.decode(encoding, errors="ignore")


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix == ".docx":
        return extract_text_from_docx(path)
    if suffix == ".txt":
        return extract_text_from_txt(path)
    return ""
