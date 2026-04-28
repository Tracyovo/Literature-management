import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Literature
from ..schemas import (
    LiteratureCreate,
    LiteratureCreateWithUpload,
    LiteratureOut,
    LiteratureUpdate,
)
from ..services.file_parser import extract_text
from ..services.fts_manager import delete_fts, upsert_fts
from ..utils import require_api_key, safe_join

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = logging.getLogger(__name__)


def _save_upload_file(upload_file: UploadFile, target_path: Path) -> None:
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


@router.post("/", response_model=LiteratureOut)
def create_literature(payload: LiteratureCreate, db: Session = Depends(get_db)):
    literature = Literature(**payload.dict())
    db.add(literature)
    db.commit()
    upsert_fts(db, literature)
    db.refresh(literature)
    return literature


@router.get("/", response_model=list[LiteratureOut])
def list_literatures(db: Session = Depends(get_db)):
    return db.query(Literature).order_by(Literature.id.desc()).all()


@router.get("/{literature_id}", response_model=LiteratureOut)
def get_literature(literature_id: int, db: Session = Depends(get_db)):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    return literature


@router.put("/{literature_id}", response_model=LiteratureOut)
def update_literature(
    literature_id: int,
    payload: LiteratureUpdate,
    db: Session = Depends(get_db),
):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(literature, field, value)
    db.commit()
    upsert_fts(db, literature)
    db.refresh(literature)
    return literature


@router.delete("/{literature_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_literature(literature_id: int, db: Session = Depends(get_db)):
    literature = db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="Literature not found")
    lit_id = literature.id
    db.delete(literature)
    db.commit()
    delete_fts(db, lit_id)
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
    target_dir = storage_root
    if subdir:
        target_dir = safe_join(storage_root, subdir)
        target_dir.mkdir(parents=True, exist_ok=True)

    target_path = safe_join(target_dir, filename)
    _save_upload_file(file, target_path)

    content_text = ""
    try:
        content_text = extract_text(target_path)
    except Exception:
        logger.exception("Failed to extract text from upload")

    literature.file_path = str(target_path)
    literature.file_name = filename
    literature.content_text = content_text
    if not literature.title:
        literature.title = Path(filename).stem
    db.commit()
    upsert_fts(db, literature)
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
    category_id: int | None = Form(default=None),
    subdir: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    payload = LiteratureCreateWithUpload(
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        abstract=abstract,
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
