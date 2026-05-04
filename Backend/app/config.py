from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List


def _resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


BASE_DIR = _resolve_base_dir()
RUNTIME_CONFIG_FILE = BASE_DIR / "storage_config.json"
AGENT_CONFIG_FILE = BASE_DIR / "agent_config.json"


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
    allowed_extensions: List[str]
    ai_provider: str
    ai_base_url: str
    ai_api_key: str
    ai_model: str
    ai_timeout_seconds: int
    ai_custom_endpoint: str
    ai_cache_ttl_seconds: int
    ai_cache_max_items: int


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


def _load_runtime_agent_config() -> dict:
    if not AGENT_CONFIG_FILE.exists():
        return {}
    try:
        payload = json.loads(AGENT_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


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
    allowed_extensions = [
        ext.lower()
        for ext in _parse_csv(os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt"))
    ]
    runtime_agent = _load_runtime_agent_config()
    ai_provider = runtime_agent.get("ai_provider") or os.getenv(
        "AI_PROVIDER", "disabled"
    )
    ai_base_url = runtime_agent.get("ai_base_url") or os.getenv("AI_BASE_URL", "")
    ai_api_key = runtime_agent.get("ai_api_key")
    if ai_api_key is None:
        ai_api_key = os.getenv("AI_API_KEY", "")
    ai_model = runtime_agent.get("ai_model")
    if ai_model is None:
        ai_model = os.getenv("AI_MODEL", "")
    timeout_value = runtime_agent.get("ai_timeout_seconds")
    if timeout_value is None:
        timeout_value = os.getenv("AI_TIMEOUT_SECONDS", "30")
    ai_timeout_seconds = int(timeout_value)
    ai_custom_endpoint = runtime_agent.get("ai_custom_endpoint")
    if ai_custom_endpoint is None:
        ai_custom_endpoint = os.getenv("AI_CUSTOM_ENDPOINT", "")
    ai_cache_ttl_seconds = int(os.getenv("AI_CACHE_TTL_SECONDS", "300"))
    ai_cache_max_items = int(os.getenv("AI_CACHE_MAX_ITEMS", "256"))
    return Settings(
        database_url=db_url,
        storage_root=storage_root,
        cors_origins=cors_origins,
        auth_enabled=auth_enabled,
        api_key=api_key,
        allowed_extensions=allowed_extensions,
        ai_provider=ai_provider,
        ai_base_url=ai_base_url,
        ai_api_key=ai_api_key,
        ai_model=ai_model,
        ai_timeout_seconds=ai_timeout_seconds,
        ai_custom_endpoint=ai_custom_endpoint,
        ai_cache_ttl_seconds=ai_cache_ttl_seconds,
        ai_cache_max_items=ai_cache_max_items,
    )


def update_storage_root(new_root: Path) -> Path:
    new_root = new_root.expanduser().resolve()
    new_root.mkdir(parents=True, exist_ok=True)
    payload = {"storage_root": str(new_root)}
    RUNTIME_CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    get_settings.cache_clear()
    return new_root


def update_agent_config(payload: dict) -> dict:
    ai_provider = (payload.get("ai_provider") or "disabled").strip()
    ai_custom_endpoint = (payload.get("ai_custom_endpoint") or "").strip()
    ai_api_key = payload.get("ai_api_key") or ""
    ai_model = (payload.get("ai_model") or "").strip()
    timeout = payload.get("ai_timeout_seconds")
    if timeout is None:
        timeout = 30
    ai_timeout_seconds = int(timeout)
    data = {
        "ai_provider": ai_provider,
        "ai_custom_endpoint": ai_custom_endpoint,
        "ai_api_key": ai_api_key,
        "ai_model": ai_model,
        "ai_timeout_seconds": ai_timeout_seconds,
    }
    AGENT_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    get_settings.cache_clear()
    return data
