from fastapi import APIRouter, Depends
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Literature
from ..schemas import LiteratureOut
from ..services.fts_manager import ensure_fts_table
from ..utils import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/", response_model=list[LiteratureOut])
def search(
    q: str = "",
    category_id: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Literature)

    keyword = q.strip()
    if keyword:
        try:
            ensure_fts_table(db)
            rows = db.execute(
                text(
                    """
                    SELECT rowid
                    FROM literatures_fts
                    WHERE literatures_fts MATCH :query
                    """
                ),
                {"query": keyword},
            ).fetchall()
            ids = [row[0] for row in rows]
            if ids:
                query = query.filter(Literature.id.in_(ids))
            else:
                return []
        except Exception:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Literature.title.ilike(like),
                    Literature.authors.ilike(like),
                    Literature.abstract.ilike(like),
                    Literature.content_text.ilike(like),
                )
            )

    if category_id is not None:
        query = query.filter(Literature.category_id == category_id)

    if year_start is not None:
        query = query.filter(Literature.year >= year_start)

    if year_end is not None:
        query = query.filter(Literature.year <= year_end)

    return query.order_by(Literature.id.desc()).all()
