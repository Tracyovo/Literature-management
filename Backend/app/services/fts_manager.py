from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Literature


def ensure_fts_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS literatures_fts
            USING fts5(
              title,
              authors,
              abstract,
              content_text,
              content='literatures',
              content_rowid='id'
            )
            """
        )
    )


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
        text(
            """
            INSERT INTO literatures_fts(rowid, title, authors, abstract, content_text)
            VALUES (:id, :title, :authors, :abstract, :content_text)
            """
        ),
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
