from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any


class SessionManager:
    def __init__(self, directory: str, max_recent_messages: int = 20):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_recent_messages = max_recent_messages
        self._lock = asyncio.Lock()

    def _path(self, session_id: str) -> Path:
        safe = "".join(char for char in session_id if char.isalnum() or char in "-_")
        if not safe:
            raise ValueError("Invalid session id.")
        return self.directory / f"{safe}.json"

    def _load(self, session_id: str) -> dict[str, Any]:
        path = self._path(session_id)
        if not path.exists():
            return {"summary": None, "messages": []}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Session '{session_id}' cannot be read.") from error
        return {"summary": payload.get("summary"), "messages": payload.get("messages", [])}

    @staticmethod
    def _summary(existing: str | None, older: list[dict[str, Any]]) -> str | None:
        pieces = [existing] if existing else []
        pieces.extend(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in older)
        return ("Earlier conversation: " + "\n".join(pieces))[-6000:] if pieces else None

    def _compact(self, summary: str | None, messages: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
        if len(messages) <= self.max_recent_messages:
            return summary, messages
        return self._summary(summary, messages[:-self.max_recent_messages]), messages[-self.max_recent_messages:]

    async def context(self, session_id: str, incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        async with self._lock:
            previous = await asyncio.to_thread(self._load, session_id)
            summary, recent = self._compact(previous["summary"], previous["messages"] + incoming)
            return ([{"role": "system", "content": summary}] if summary else []) + recent

    async def save(self, session_id: str, new_messages: list[dict[str, Any]]) -> None:
        async with self._lock:
            previous = await asyncio.to_thread(self._load, session_id)
            summary, recent = self._compact(previous["summary"], previous["messages"] + new_messages)
            payload = json.dumps({"summary": summary, "messages": recent}, ensure_ascii=False)
            await asyncio.to_thread(self._path(session_id).write_text, payload, encoding="utf-8")
