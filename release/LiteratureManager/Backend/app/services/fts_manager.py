from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Literature

DEFAULT_BM25_WEIGHTS = (3.0, 2.0, 1.5, 1.0)


def ensure_fts_table(db: Session) -> None:
    db.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS literatures_fts
            USING fts5(
              title,
              authors,
              abstract,
              content_text,
              content='literatures',
              content_rowid='id'
            )
            """))


def rebuild_fts(db: Session) -> None:
    ensure_fts_table(db)
    db.execute(text("INSERT INTO literatures_fts(literatures_fts) VALUES('rebuild')"))


def upsert_fts(db: Session, literature: Literature) -> None:
    ensure_fts_table(db)
    db.execute(
        text(
            "INSERT INTO literatures_fts(literatures_fts, rowid) VALUES('delete', :id)"
        ),
        {"id": literature.id},
    )
    db.execute(
        text("""
            INSERT INTO literatures_fts(rowid, title, authors, abstract, content_text)
            VALUES (:id, :title, :authors, :abstract, :content_text)
            """),
        {
            "id": literature.id,
            "title": literature.title or "",
            "authors": literature.authors or "",
            "abstract": literature.abstract or "",
            "content_text": literature.content_text or "",
        },
    )


def delete_fts(db: Session, literature_id: int) -> None:
    ensure_fts_table(db)
    db.execute(
        text(
            "INSERT INTO literatures_fts(literatures_fts, rowid) VALUES('delete', :id)"
        ),
        {"id": literature_id},
    )


def build_bm25_expression(
    weights: tuple[float, float, float, float] = DEFAULT_BM25_WEIGHTS,
) -> str:
    w_title, w_authors, w_abstract, w_content = weights
    return (
        "bm25(literatures_fts, " f"{w_title}, {w_authors}, {w_abstract}, {w_content})"
    )


def build_highlight_expression(
    column: str,
    start_tag: str,
    end_tag: str,
    ellipsis: str = "...",
) -> str:
    return "snippet(literatures_fts, " f"{column}, :start_tag, :end_tag, :ellipsis, 12)"
