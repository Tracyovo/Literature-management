from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    created_at: float
    expires_at: float
    value: dict[str, Any]


class AgentMemory:
    def __init__(self, ttl_seconds: int = 300, max_items: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max(1, max_items)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

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
        self._cache.move_to_end(key)
        return entry.value

    def set(self, key: str, value: dict[str, Any]) -> None:
        now = time.time()
        expires_at = now + self.ttl_seconds
        self._cache[key] = CacheEntry(
            created_at=now,
            expires_at=expires_at,
            value=value,
        )
        self._cache.move_to_end(key)
        self._prune()

    def _prune(self) -> None:
        now = time.time()
        expired = [key for key, entry in self._cache.items() if entry.expires_at < now]
        for key in expired:
            self._cache.pop(key, None)
        while len(self._cache) > self.max_items:
            self._cache.popitem(last=False)
