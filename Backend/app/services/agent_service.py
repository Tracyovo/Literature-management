from __future__ import annotations

import json
import re

import httpx

from ..config import get_settings
from .agent_memory import AgentMemory
from .agent_tools import extract_basic_metadata


class AgentService:
    def __init__(self, memory: AgentMemory | None = None) -> None:
        self.settings = get_settings()
        self.memory = memory or AgentMemory(
            ttl_seconds=self.settings.ai_cache_ttl_seconds,
            max_items=self.settings.ai_cache_max_items,
        )

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

        payload = None
        if self._ai_enabled():
            payload = self._call_ai(text=text, filename=filename)

        if payload:
            payload = self._normalize_payload(payload)
        else:
            suggestion = extract_basic_metadata(text, filename)
            payload = self._build_payload(suggestion)
        self.memory.set(cache_key, payload)
        return payload

    def get_status(self) -> dict:
        if not self._ai_enabled():
            return {"available": False, "mode": "rules", "model": None}
        return {
            "available": True,
            "mode": self.settings.ai_provider,
            "model": self.settings.ai_model or None,
        }

    def _ai_enabled(self) -> bool:
        provider = self.settings.ai_provider.lower()
        if provider == "openai":
            return bool(
                self.settings.ai_base_url
                and self.settings.ai_api_key
                and self.settings.ai_model
            )
        if provider in {"custom", "api"}:
            return bool(self.settings.ai_custom_endpoint and self.settings.ai_model)
        return False

    def _call_ai(self, *, text: str, filename: str | None) -> dict | None:
        provider = self.settings.ai_provider.lower()
        if provider == "openai":
            return self._call_openai(text=text, filename=filename)
        if provider in {"custom", "api"}:
            return self._call_custom(text=text, filename=filename)
        return None

    def _call_openai(self, *, text: str, filename: str | None) -> dict | None:
        prompt = self._build_prompt(text, filename)
        base = self.settings.ai_base_url.rstrip("/")
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.ai_api_key}"}
        payload = {
            "model": self.settings.ai_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a metadata extraction assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            with httpx.Client(timeout=self.settings.ai_timeout_seconds) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return None

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return self._parse_json(content)

    def _call_custom(self, *, text: str, filename: str | None) -> dict | None:
        payload = {
            "text": text,
            "filename": filename,
            "model": self.settings.ai_model,
        }
        headers = {}
        if self.settings.ai_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ai_api_key}"
        try:
            with httpx.Client(timeout=self.settings.ai_timeout_seconds) as client:
                resp = client.post(
                    self.settings.ai_custom_endpoint, json=payload, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return None
        if isinstance(data, dict):
            return {
                "title": data.get("title"),
                "authors": data.get("authors"),
                "year": data.get("year"),
                "category_suggest": data.get("category_suggest"),
            }
        return None

    def _build_prompt(self, text: str, filename: str | None) -> str:
        snippet = (text or "")[:2000]
        name = filename or ""
        return (
            "Extract metadata in JSON with keys: title, authors, year, category_suggest.\n"
            "Use null for missing values. Only output JSON.\n"
            f"Filename: {name}\n"
            f"Content:\n{snippet}\n"
        )

    def _parse_json(self, content: str) -> dict | None:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        cleaned = self._strip_code_fences(content)
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _strip_code_fences(self, content: str) -> str:
        return re.sub(r"^```[a-zA-Z]*\n|```$", "", content.strip())

    def _normalize_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {}
        title = payload.get("title")
        authors = payload.get("authors")
        year = payload.get("year")
        category = payload.get("category_suggest")
        if isinstance(year, str) and year.isdigit():
            year = int(year)
        return {
            "title": title or None,
            "authors": authors or None,
            "year": year if isinstance(year, int) else None,
            "category_suggest": category or None,
        }

    def _build_payload(self, suggestion) -> dict:
        return {
            "title": suggestion.title,
            "authors": suggestion.authors,
            "year": suggestion.year,
            "category_suggest": suggestion.category_suggest,
        }
