from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings, update_agent_config, update_storage_root
from ..schemas import AgentConfig, StorageRootUpdate
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


@router.get("/agent", response_model=AgentConfig)
def get_agent_config():
    settings = get_settings()
    return AgentConfig(
        ai_provider=settings.ai_provider,
        ai_custom_endpoint=settings.ai_custom_endpoint,
        ai_api_key="" if settings.ai_api_key else None,
        ai_model=settings.ai_model,
        ai_timeout_seconds=settings.ai_timeout_seconds,
    )


@router.put("/agent", response_model=AgentConfig)
def set_agent_config(payload: AgentConfig):
    data = update_agent_config(payload.dict())
    return AgentConfig(**data)
