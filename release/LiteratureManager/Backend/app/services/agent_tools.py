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
        if not clean:
            continue
        lower = clean.lower()
        if lower.startswith(("abstract", "keywords", "doi")):
            continue
        if len(clean) < 5 or len(clean) > 160:
            continue
        return clean
    return None


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _extract_authors(text: str) -> str | None:
    for line in text.splitlines()[:20]:
        clean = _normalize_line(line)
        lower = clean.lower()
        if lower.startswith("author") or lower.startswith("authors"):
            parts = re.split(r"[:：]", clean, maxsplit=1)
            if len(parts) == 2:
                return parts[1].strip() or None
            return clean
        if lower.startswith("by "):
            return clean[3:].strip() or None
    return None


def extract_basic_metadata(text: str, filename: str | None) -> MetadataSuggestion:
    title = _first_non_empty_line(text)
    if not title and filename:
        title = Path(filename).stem

    authors = _extract_authors(text)

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
        "deep learning": "Machine Learning",
        "reinforcement learning": "Machine Learning",
        "computer vision": "Computer Vision",
        "natural language": "Natural Language Processing",
        "nlp": "Natural Language Processing",
        "information retrieval": "Information Retrieval",
        "graph": "Graph Learning",
        "quantum": "Quantum Computing",
        "large language model": "Large Language Models",
        "llm": "Large Language Models",
    }
    for keyword, category in keyword_map.items():
        if keyword in lower:
            return category
    return None
