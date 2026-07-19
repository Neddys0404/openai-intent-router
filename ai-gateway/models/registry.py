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
    startup_timeout: float = 300.0
    persistent: bool = False


class ModelRegistry:
    def __init__(self, raw_models: dict[str, Any], default_timeout: float = 600.0):
        self._models = {
            name: ModelDefinition(
                name=name,
                endpoint=spec["endpoint"].rstrip("/"),
                timeout=float(spec.get("timeout", default_timeout)),
                health_path=spec.get("health_path", "/models"),
                start_command=spec.get("start_command"),
                startup_timeout=float(spec.get("startup_timeout", 300)),
                persistent=bool(spec.get("persistent", False)),
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
