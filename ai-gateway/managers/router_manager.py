from __future__ import annotations

from typing import Any
from llm.classifier import KeywordClassifier


class RouterManager:
    def __init__(self, routes: dict[str, Any]):
        self.routes = routes
        self.classifier = KeywordClassifier(routes)

    def choose_model(self, requested_model: str | None, messages: list[dict[str, Any]]) -> tuple[str, str]:
        if requested_model and requested_model not in {"auto", "gateway"}:
            return requested_model, "explicit"
        route = self.classifier.classify(messages)
        try:
            return self.routes[route]["model"], route
        except KeyError as error:
            raise ValueError(f"Route '{route}' has no configured model.") from error
