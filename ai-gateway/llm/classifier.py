from __future__ import annotations

from typing import Any


class KeywordClassifier:
    """Small deterministic router; replace with a classifier model when needed."""

    def __init__(self, routes: dict[str, Any]):
        self.routes = routes

    def classify(self, messages: list[dict[str, Any]]) -> str:
        text = " ".join(str(item.get("content", "")) for item in messages if item.get("role") == "user").lower()
        for route_name, route in self.routes.items():
            if any(keyword.lower() in text for keyword in route.get("keywords", [])):
                return route_name
        return "chat" if "chat" in self.routes else next(iter(self.routes))
