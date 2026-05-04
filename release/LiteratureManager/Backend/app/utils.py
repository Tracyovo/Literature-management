from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import Header, HTTPException, status

from .config import get_settings


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def safe_join(base: Path, *paths: str) -> Path:
    base = base.resolve()
    target = base.joinpath(*paths).resolve()
    if os.path.commonpath([base, target]) != str(base):
        raise ValueError("Invalid path")
    return target


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.auth_enabled:
        return
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
