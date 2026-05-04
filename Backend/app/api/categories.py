from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Category, Literature
from ..schemas import CategoryCreate, CategoryOut, CategoryUpdate
from ..utils import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    category = Category(name=payload.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name.asc()).all()


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    has_items = (
        db.query(Literature).filter(Literature.category_id == category_id).first()
    )
    if has_items:
        raise HTTPException(
            status_code=400,
            detail="Category has literatures; move them first",
        )
    db.delete(category)
    db.commit()
    return None


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    existing = db.query(Category).filter(Category.name == payload.name).first()
    if existing and existing.id != category_id:
        raise HTTPException(status_code=400, detail="Category already exists")
    category.name = payload.name
    db.commit()
    db.refresh(category)
    return category
