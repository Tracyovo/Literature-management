import csv
import io
import logging
import os
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Category, Literature
from ..schemas import (
    ImportErrorDetail,
    ImportResult,
    LiteratureCreate,
    LiteratureCreateWithUpload,
    LiteratureOut,
    LiteratureUpdate,
)
from ..services.file_parser import extract_text
from ..services.fts_manager import (
    build_bm25_expression,
    delete_fts,
    ensure_fts_table,
    upsert_fts,
)
from ..utils import require_api_key, safe_join

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = logging.getLogger(__name__)

ALLOWED_SORT_FIELDS = {
    "id": Literature.id,
    "title": Literature.title,
    "year": Literature.year,
    "created_at": Literature.created_at,
    "updated_at": Literature.updated_at,
}

SIMILARITY_MAX_TERMS = 8


def _save_upload_file(upload_file: UploadFile, target_path: Path) -> None:
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


def _unique_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _safe_remove(path: Path, base_dir: Path) -> None:
    try:
        base = base_dir.resolve()
        target = path.resolve()
        if os.path.commonpath([base, target]) != str(base):
            return
        if target.exists():
            target.unlink()
    except OSError:
        logger.exception("Failed to remove old file")


def _get_or_create_category(db: Session, name: str) -> int | None:
    clean = name.strip()
    if not clean:
        return None
    existing = db.query(Category).filter(Category.name == clean).first()
    if existing:
        return existing.id
    category = Category(name=clean)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category.id


def _parse_bibtex_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for match in re.finditer(r"@\w+\s*\{([\s\S]*?)\}\s*", text):
        body = match.group(1)
        fields: dict[str, str] = {}
        for kv in re.finditer(r"(\w+)\s*=\s*\{([\s\S]*?)\}\s*,?", body):
            key = kv.group(1).strip().lower()
            value = kv.group(2).strip()
            fields[key] = value
        if fields:
            entries.append(fields)
    return entries


def _serialize_bibtex(items: list[Literature], categories: dict[int, str]) -> str:
    lines: list[str] = []
    for item in items:
        key = f"lit{item.id}"
        lines.append(f"@article{{{key},")
        lines.append(f"  title={{{item.title}}},")
        if item.authors:
            lines.append(f"  author={{{item.authors}}},")
        if item.year:
            lines.append(f"  year={{{item.year}}},")
        if item.journal:
            lines.append(f"  journal={{{item.journal}}},")
        if item.abstract:
            lines.append(f"  abstract={{{item.abstract}}},")
        if item.citation:
            lines.append(f"  note={{{item.citation}}},")
        category = categories.get(item.category_id or 0)
        if category:
            lines.append(f"  keywords={{{category}}},")
        lines.append("}")
        lines.append("")
    return "\n".join(lines).strip()


def _build_similarity_query(item: Literature) -> str:
    source = " ".join(
        [
            item.title or "",
            item.authors or "",
            item.abstract or "",
        ]
    )
    terms = re.findall(r"[A-Za-z0-9]{4,}", source)
    unique = []
    for term in terms:
        term_lower = term.lower()
        if term_lower not in unique:
            unique.append(term_lower)
        if len(unique) >= SIMILARITY_MAX_TERMS:
            break
    return " OR ".join(unique)


def _analyze_citation(citation: str | None) -> dict:
    if not citation:
        return {"years": [], "year_count": 0, "has_doi": False}
    years = sorted({int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", citation)})
    has_doi = bool(re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", citation))
    return {"years": years, "year_count": len(years), "has_doi": has_doi}


@router.post("/", response_model=LiteratureOut)
def create_literature(payload: LiteratureCreate, db: Session = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    data = payload.dict()
    data["title"] = title
    literature = Literature(**data)
    db.add(literature)
    db.commit()
    try:
        upsert_fts(db, literature)
    except Exception:
        logger.exception("Failed to update FTS index")
    db.refresh(literature)
    return literature


@router.get("/", response_model=list[LiteratureOut])
def list_literatures(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "id",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    sort_column = ALLOWED_SORT_FIELDS.get(sort_by, Literature.id)
    order_expr = (
        sort_column.desc() if sort_order.lower() == "desc" else sort_column.asc()
    )
    return db.query(Literature).order_by(order_expr).offset(offset).limit(limit).all()


@router.get("/{literature_id}", response_model=LiteratureOut)
def get_literature(literature_id: int, db: Session = Depends(get_db)):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    return literature


@router.get("/{literature_id}/similar", response_model=list[LiteratureOut])
def get_similar_literatures(
    literature_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    query_terms = _build_similarity_query(literature)
    if not query_terms:
        return []
    limit = max(1, min(limit, 20))

    try:
        ensure_fts_table(db)
        bm25_expr = build_bm25_expression()
        rows = db.execute(
            text("""
                SELECT rowid, {bm25} AS score
                FROM literatures_fts
                WHERE literatures_fts MATCH :query
                ORDER BY score ASC
                LIMIT :limit
                """.format(bm25=bm25_expr)),
            {"query": query_terms, "limit": limit + 1},
        ).fetchall()
        ids = [row[0] for row in rows if row[0] != literature.id]
        if not ids:
            return []
        if len(ids) > limit:
            ids = ids[:limit]
        return db.query(Literature).filter(Literature.id.in_(ids)).all()
    except Exception:
        keyword = (literature.title or "").split(" ")[0:1]
        if not keyword:
            return []
        like = f"%{keyword[0]}%"
        return (
            db.query(Literature)
            .filter(Literature.id != literature.id)
            .filter((Literature.title.ilike(like)) | (Literature.abstract.ilike(like)))
            .limit(limit)
            .all()
        )


@router.get("/{literature_id}/citation-analysis")
def citation_analysis(literature_id: int, db: Session = Depends(get_db)):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    return _analyze_citation(literature.citation)


@router.put("/{literature_id}", response_model=LiteratureOut)
def update_literature(
    literature_id: int,
    payload: LiteratureUpdate,
    db: Session = Depends(get_db),
):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    updates = payload.dict(exclude_unset=True)
    if "title" in updates:
        title = (updates["title"] or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Title is required")
        updates["title"] = title
    for field, value in updates.items():
        setattr(literature, field, value)
    db.commit()
    try:
        upsert_fts(db, literature)
    except Exception:
        logger.exception("Failed to update FTS index")
    db.refresh(literature)
    return literature


@router.delete("/{literature_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_literature(literature_id: int, db: Session = Depends(get_db)):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    lit_id = literature.id
    file_path = literature.file_path
    db.delete(literature)
    db.commit()
    try:
        delete_fts(db, lit_id)
    except Exception:
        logger.exception("Failed to delete FTS index")
    if file_path:
        settings = get_settings()
        _safe_remove(Path(file_path), settings.storage_root)
    return None


@router.post("/{literature_id}/upload", response_model=LiteratureOut)
def upload_file(
    literature_id: int,
    file: UploadFile = File(...),
    subdir: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    settings = get_settings()
    storage_root = settings.storage_root
    storage_root.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "uploaded.bin"
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension and extension not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    target_dir = storage_root
    if subdir:
        try:
            target_dir = safe_join(storage_root, subdir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        target_dir.mkdir(parents=True, exist_ok=True)

    try:
        target_path = safe_join(target_dir, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    target_path = _unique_path(target_path)
    if literature.file_path:
        _safe_remove(Path(literature.file_path), storage_root)
    _save_upload_file(file, target_path)

    content_text = ""
    try:
        content_text = extract_text(target_path)
    except Exception:
        logger.exception("Failed to extract text from upload")

    literature.file_path = str(target_path)
    literature.file_name = target_path.name
    literature.content_text = content_text
    if not literature.title:
        literature.title = target_path.stem
    db.commit()
    try:
        upsert_fts(db, literature)
    except Exception:
        logger.exception("Failed to update FTS index")
    db.refresh(literature)
    return literature


@router.post("/upload", response_model=LiteratureOut)
def create_with_upload(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    authors: str | None = Form(default=None),
    year: int | None = Form(default=None),
    journal: str | None = Form(default=None),
    abstract: str | None = Form(default=None),
    citation: str | None = Form(default=None),
    category_id: int | None = Form(default=None),
    subdir: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    extension = Path(file.filename or "").suffix.lower().lstrip(".")
    if extension and extension not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if not title:
        title = Path(file.filename or "uploaded").stem
    payload = LiteratureCreateWithUpload(
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        abstract=abstract,
        citation=citation,
        category_id=category_id,
    )
    literature = Literature(**payload.dict(exclude_unset=True))
    db.add(literature)
    db.commit()
    db.refresh(literature)

    return upload_file(
        literature_id=literature.id,
        file=file,
        subdir=subdir,
        db=db,
    )


@router.get("/export", response_class=PlainTextResponse)
def export_literatures(
    format: str = "csv",
    db: Session = Depends(get_db),
):
    items = db.query(Literature).order_by(Literature.id.asc()).all()
    categories = {c.id: c.name for c in db.query(Category).all()}

    if format == "bibtex":
        content = _serialize_bibtex(items, categories)
        return PlainTextResponse(content or "")

    if format != "csv":
        raise HTTPException(status_code=400, detail="Unsupported export format")

    output = [
        [
            "title",
            "authors",
            "year",
            "journal",
            "abstract",
            "citation",
            "category",
        ]
    ]
    for item in items:
        output.append(
            [
                item.title,
                item.authors or "",
                str(item.year or ""),
                item.journal or "",
                item.abstract or "",
                item.citation or "",
                categories.get(item.category_id or 0, ""),
            ]
        )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in output:
        writer.writerow(row)
    return PlainTextResponse(buffer.getvalue().strip())


@router.post("/import", response_model=ImportResult)
def import_literatures(
    file: UploadFile = File(...),
    format: str = Form(default="csv"),
    db: Session = Depends(get_db),
):
    content = file.file.read().decode("utf-8", errors="ignore")

    if format == "bibtex":
        entries = _parse_bibtex_entries(content)
        created = 0
        skipped = 0
        errors: list[ImportErrorDetail] = []
        for index, entry in enumerate(entries, start=1):
            title = entry.get("title")
            if not title:
                skipped += 1
                continue
            category_name = entry.get("keywords", "")
            category_id = _get_or_create_category(db, category_name)
            year_value = entry.get("year")
            year = None
            if year_value:
                if str(year_value).isdigit():
                    year = int(year_value)
                else:
                    errors.append(
                        ImportErrorDetail(
                            row=index,
                            reason="Invalid year value",
                        )
                    )
                    skipped += 1
                    continue
            literature = Literature(
                title=title,
                authors=entry.get("author"),
                year=year,
                journal=entry.get("journal"),
                abstract=entry.get("abstract"),
                citation=entry.get("note"),
                category_id=category_id,
            )
            db.add(literature)
            db.commit()
            db.refresh(literature)
            try:
                upsert_fts(db, literature)
            except Exception:
                logger.exception("Failed to update FTS index")
            created += 1
        return ImportResult(created=created, skipped=skipped, errors=errors)

    if format != "csv":
        raise HTTPException(status_code=400, detail="Unsupported import format")

    reader = csv.DictReader(content.splitlines())
    created = 0
    skipped = 0
    errors: list[ImportErrorDetail] = []
    for index, row in enumerate(reader, start=2):
        title = (row.get("title") or "").strip()
        if not title:
            skipped += 1
            continue
        category_id = _get_or_create_category(db, row.get("category", ""))
        year_value = (row.get("year") or "").strip()
        year = None
        if year_value:
            if year_value.isdigit():
                year = int(year_value)
            else:
                errors.append(
                    ImportErrorDetail(
                        row=index,
                        reason="Invalid year value",
                    )
                )
                skipped += 1
                continue
        literature = Literature(
            title=title,
            authors=row.get("authors") or None,
            year=year,
            journal=row.get("journal") or None,
            abstract=row.get("abstract") or None,
            citation=row.get("citation") or None,
            category_id=category_id,
        )
        db.add(literature)
        db.commit()
        db.refresh(literature)
        try:
            upsert_fts(db, literature)
        except Exception:
            logger.exception("Failed to update FTS index")
        created += 1

    return ImportResult(created=created, skipped=skipped, errors=errors)
