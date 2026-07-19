from __future__ import annotations

from typing import Any

from llm.classifier import LLMClassifier
from models.registry import ModelRegistry


class RouterManager:
    def __init__(self, routes: dict[str, Any], registry: ModelRegistry, classifier_model: str, classifier_timeout: float = 20):
        self.routes = routes
        self.registry = registry
        self.classifier_model = classifier_model
        self.classifier = LLMClassifier(routes, classifier_model, classifier_timeout)

    async def choose_model(self, requested_model: str | None, messages: list[dict[str, Any]]) -> tuple[str, str]:
        if requested_model and requested_model not in {"auto", "gateway"}:
            return requested_model, "explicit"
        classifier_definition = self.registry.get(self.classifier_model)
        route = await self.classifier.classify(classifier_definition.endpoint, messages)
        try:
            return self.routes[route]["model"], route
        except KeyError as error:
            raise ValueError(f"Route '{route}' has no configured model.") from error
