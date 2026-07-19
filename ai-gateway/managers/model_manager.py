from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any
import httpx
import yaml

from models.registry import ModelRegistry


class ModelManager:
    def __init__(self, config_path: str | Path | None = None):
        config_path = Path(config_path or Path(__file__).parents[1] / "config.yaml")
        self.config: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        self.registry = ModelRegistry(self.config.get("models", {}))
        self.models = {name: self.registry.get(name) for name in self.registry.names()}
        self.active_model: str | None = None
        self.last_used: float | None = None
        self.requests = 0
        self.started_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def get_endpoint(self, model_name: str) -> str:
        await self.ensure_ready(model_name)
        return self.registry.get(model_name).endpoint

    async def is_running(self, model_name: str) -> bool:
        model = self.registry.get(model_name)
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(model.endpoint + model.health_path)
            return response.is_success
        except httpx.HTTPError:
            return False

    async def ensure_ready(self, model_name: str) -> None:
        model = self.registry.get(model_name)
        async with self._lock:
            if not await self.is_running(model_name):
                if not model.start_command:
                    raise RuntimeError(f"Model '{model_name}' is unavailable at {model.endpoint}. Start its server or configure start_command.")
                subprocess.Popen(model.start_command, shell=True)  # Config is operator-controlled.
                for _ in range(30):
                    await asyncio.sleep(1)
                    if await self.is_running(model_name):
                        break
                else:
                    raise RuntimeError(f"Model '{model_name}' did not become ready.")
            self.active_model, self.last_used = model_name, time.monotonic()
            self.requests += 1

    async def unload_if_idle(self) -> None:
        timeout = float(self.config.get("gateway", {}).get("idle_timeout_seconds", 600))
        if self.active_model and self.last_used and time.monotonic() - self.last_used > timeout:
            self.active_model = None

    def health(self) -> dict[str, Any]:
        return {"active_model": self.active_model, "requests": self.requests, "uptime_seconds": round(time.monotonic() - self.started_at, 1)}


model_manager = ModelManager()
