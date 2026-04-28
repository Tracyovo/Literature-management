from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MetadataSuggestion:
    title: str | None
    authors: str | None
    year: int | None
    category_suggest: str | None


def read_text_from_path(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    if path.suffix.lower() != ".txt":
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text[:max_chars]


def _first_non_empty_line(text: str) -> str | None:
    for line in text.splitlines():
        clean = line.strip()
        if clean:
            return clean
    return None


def extract_basic_metadata(text: str, filename: str | None) -> MetadataSuggestion:
    title = _first_non_empty_line(text)
    if not title and filename:
        title = Path(filename).stem

    authors = None
    for line in text.splitlines():
        if "author" in line.lower():
            authors = line.strip()
            break

    year = None
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if match:
        year = int(match.group(0))

    category_suggest = suggest_category(text)

    return MetadataSuggestion(
        title=title,
        authors=authors,
        year=year,
        category_suggest=category_suggest,
    )


def suggest_category(text: str) -> str | None:
    lower = text.lower()
    keyword_map = {
        "machine learning": "Machine Learning",
        "neural network": "Machine Learning",
        "natural language": "Natural Language Processing",
        "nlp": "Natural Language Processing",
        "quantum": "Quantum Computing",
    }
    for keyword, category in keyword_map.items():
        if keyword in lower:
            return category
    return None
