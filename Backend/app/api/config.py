from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings, update_agent_config, update_storage_root
from ..schemas import AgentConfig, StorageRootUpdate
from ..utils import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


def _build_storage_tree(
    base_dir: Path,
    current_dir: Path,
    depth: int,
    max_entries: int,
) -> list[dict]:
    if depth <= 0:
        return []
    try:
        entries = sorted(
            [
                entry
                for entry in current_dir.iterdir()
                if entry.is_dir() and not entry.is_symlink()
            ],
            key=lambda entry: entry.name.lower(),
        )
    except OSError:
        return []

    nodes: list[dict] = []
    for entry in entries[:max_entries]:
        node = {
            "name": entry.name,
            "path": str(entry.relative_to(base_dir)),
        }
        children = _build_storage_tree(
            base_dir,
            entry,
            depth - 1,
            max_entries,
        )
        if children:
            node["children"] = children
        nodes.append(node)
    return nodes


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


@router.get("/storage-tree")
def get_storage_tree(depth: int = 3, max_entries: int = 200):
    depth = max(1, min(depth, 6))
    max_entries = max(1, min(max_entries, 500))
    settings = get_settings()
    root = settings.storage_root
    root.mkdir(parents=True, exist_ok=True)
    nodes = _build_storage_tree(root, root, depth, max_entries)
    return {"root": str(root), "nodes": nodes}


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
