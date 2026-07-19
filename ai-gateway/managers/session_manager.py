from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from llm.summarizer import compact_messages


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

    async def context(self, session_id: str, incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        async with self._lock:
            path = self._path(session_id)
            previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"messages": []}
            messages = previous.get("messages", []) + incoming
            summary, recent = compact_messages(messages, self.max_recent_messages)
            saved_summary = previous.get("summary")
            active_summary = summary or saved_summary
            return ([{"role": "system", "content": active_summary}] if active_summary else []) + recent

    async def save(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        async with self._lock:
            summary, recent = compact_messages(messages, self.max_recent_messages)
            payload = {"summary": summary, "messages": recent}
            self._path(session_id).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
