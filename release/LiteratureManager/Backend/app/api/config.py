from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings, update_storage_root
from ..schemas import StorageRootUpdate
from ..utils import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/storage-root")
def get_storage_root():
    settings = get_settings()
    return {"storage_root": str(settings.storage_root)}


@router.put("/storage-root")
def set_storage_root(payload: StorageRootUpdate):
    try:
        new_root = update_storage_root(Path(payload.storage_root))
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"storage_root": str(new_root)}
