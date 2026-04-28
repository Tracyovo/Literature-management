from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    expires_at: float
    value: dict[str, Any]


class AgentMemory:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}

    def build_key(
        self,
        *,
        text: str,
        filename: str | None = None,
        literature_id: int | None = None,
    ) -> str:
        parts = [text or "", filename or "", str(literature_id or "")]
        digest = hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
        return digest

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self._cache.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: dict[str, Any]) -> None:
        expires_at = time.time() + self.ttl_seconds
        self._cache[key] = CacheEntry(expires_at=expires_at, value=value)
