from __future__ import annotations

from .agent_memory import AgentMemory
from .agent_tools import extract_basic_metadata


class AgentService:
    def __init__(self, memory: AgentMemory | None = None) -> None:
        self.memory = memory or AgentMemory()

    def suggest_metadata(
        self,
        *,
        text: str,
        filename: str | None = None,
        literature_id: int | None = None,
    ) -> dict:
        cache_key = self.memory.build_key(
            text=text,
            filename=filename,
            literature_id=literature_id,
        )
        cached = self.memory.get(cache_key)
        if cached:
            return cached

        suggestion = extract_basic_metadata(text, filename)
        payload = {
            "title": suggestion.title,
            "authors": suggestion.authors,
            "year": suggestion.year,
            "category_suggest": suggestion.category_suggest,
        }
        self.memory.set(cache_key, payload)
        return payload

    def get_status(self) -> dict:
        return {"available": True, "mode": "rules"}
