from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_CONFIG_FILE = BASE_DIR / "storage_config.json"


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str
    storage_root: Path
    cors_origins: List[str]
    auth_enabled: bool
    api_key: str


def _load_runtime_storage_root() -> Path | None:
    if not RUNTIME_CONFIG_FILE.exists():
        return None
    try:
        payload = json.loads(RUNTIME_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    value = payload.get("storage_root")
    if not value:
        return None
    return Path(value)


def _default_storage_root() -> Path:
    return BASE_DIR / "uploads"


def _resolve_storage_root() -> Path:
    env_root = os.getenv("STORAGE_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    runtime_root = _load_runtime_storage_root()
    if runtime_root:
        return runtime_root
    return _default_storage_root()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    db_path = os.getenv("DB_PATH", str(BASE_DIR / "store.db"))
    db_url = f"sqlite:///{Path(db_path).as_posix()}"
    storage_root = _resolve_storage_root()
    cors_origins = _parse_csv(os.getenv("CORS_ORIGINS", "*"))
    auth_enabled = _parse_bool(os.getenv("AUTH_ENABLED"), default=False)
    api_key = os.getenv("API_KEY", "change-me")
    return Settings(
        database_url=db_url,
        storage_root=storage_root,
        cors_origins=cors_origins,
        auth_enabled=auth_enabled,
        api_key=api_key,
    )


def update_storage_root(new_root: Path) -> Path:
    new_root = new_root.expanduser().resolve()
    new_root.mkdir(parents=True, exist_ok=True)
    payload = {"storage_root": str(new_root)}
    RUNTIME_CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    get_settings.cache_clear()
    return new_root
