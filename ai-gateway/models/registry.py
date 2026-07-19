from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelDefinition:
    name: str
    endpoint: str
    timeout: float = 600.0
    health_path: str = "/models"
    start_command: str | None = None


class ModelRegistry:
    def __init__(self, raw_models: dict[str, Any]):
        self._models = {
            name: ModelDefinition(
                name=name,
                endpoint=spec["endpoint"].rstrip("/"),
                timeout=float(spec.get("timeout", 600)),
                health_path=spec.get("health_path", "/models"),
                start_command=spec.get("start_command"),
            )
            for name, spec in raw_models.items()
        }

    def get(self, name: str) -> ModelDefinition:
        try:
            return self._models[name]
        except KeyError as error:
            raise ValueError(f"Model '{name}' is not configured.") from error

    def names(self) -> list[str]:
        return list(self._models)
