from fastapi import APIRouter, Depends
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Literature
from ..schemas import SearchHit, SearchHighlights, SearchResponse
from ..services.fts_manager import build_bm25_expression, ensure_fts_table
from ..utils import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])

ALLOWED_SORT_FIELDS = {
    "id": Literature.id,
    "title": Literature.title,
    "year": Literature.year,
    "created_at": Literature.created_at,
    "updated_at": Literature.updated_at,
}


@router.get("/", response_model=SearchResponse)
def search(
    q: str = "",
    category_id: int | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "id",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    query = db.query(Literature)

    keyword = q.strip()
    if keyword:
        try:
            ensure_fts_table(db)
            bm25_expr = build_bm25_expression()
            params = {
                "query": keyword,
                "start_tag": "<mark>",
                "end_tag": "</mark>",
                "ellipsis": "...",
            }
            rows = db.execute(
                text("""
                    SELECT
                        rowid,
                        {bm25} AS score,
                        snippet(literatures_fts, 0, :start_tag, :end_tag, :ellipsis, 12) AS h_title,
                        snippet(literatures_fts, 1, :start_tag, :end_tag, :ellipsis, 12) AS h_authors,
                        snippet(literatures_fts, 2, :start_tag, :end_tag, :ellipsis, 12) AS h_abstract,
                        snippet(literatures_fts, 3, :start_tag, :end_tag, :ellipsis, 12) AS h_content
                    FROM literatures_fts
                    WHERE literatures_fts MATCH :query
                    """.format(bm25=bm25_expr)),
                params,
            ).fetchall()
            ids = [row[0] for row in rows]
            if not ids:
                return SearchResponse(total=0, limit=limit, offset=offset, items=[])
            score_map = {row[0]: float(row[1]) for row in rows}
            highlight_map = {
                row[0]: SearchHighlights(
                    title=row[2],
                    authors=row[3],
                    abstract=row[4],
                    content_text=row[5],
                )
                for row in rows
            }
            query = query.filter(Literature.id.in_(ids))
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
            score_map = {}
            highlight_map = {}
    else:
        score_map = {}
        highlight_map = {}

    if category_id is not None:
        query = query.filter(Literature.category_id == category_id)

    if year_start is not None:
        query = query.filter(Literature.year >= year_start)

    if year_end is not None:
        query = query.filter(Literature.year <= year_end)

    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    sort_column = ALLOWED_SORT_FIELDS.get(sort_by, Literature.id)
    order_expr = (
        sort_column.desc() if sort_order.lower() == "desc" else sort_column.asc()
    )

    total = query.count()
    items = query.order_by(order_expr).offset(offset).limit(limit).all()
    hits = [
        SearchHit(
            literature=item,
            score=score_map.get(item.id),
            highlights=highlight_map.get(item.id),
        )
        for item in items
    ]
    return SearchResponse(total=total, limit=limit, offset=offset, items=hits)
