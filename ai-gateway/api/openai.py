from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx

from llm.client import UpstreamClient
from managers.model_manager import model_manager
from managers.router_manager import RouterManager
from managers.session_manager import SessionManager

router = APIRouter()
client = UpstreamClient()
gateway_config = model_manager.config.get("gateway", {})
router_manager = RouterManager(
    model_manager.config.get("routes", {}),
    model_manager.registry,
    gateway_config.get("classifier_model", "chat"),
    gateway_config.get("classifier_timeout", 20),
)
session_manager = SessionManager(gateway_config.get("session_directory", "sessions"), gateway_config.get("max_recent_messages", 20))


def _authorize(request: Request) -> None:
    api_key = gateway_config.get("api_key")
    if api_key and request.headers.get("authorization") != f"Bearer {api_key}":
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/chat/completions")
async def chat_completions(request: Request):
    _authorize(request)
    try:
        body: dict[str, Any] = await request.json()
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("'messages' must be a non-empty list.")
        if not body.get("model") or body.get("model") in {"auto", "gateway"}:
            await model_manager.get_endpoint(router_manager.classifier_model)
        model_name, route = await router_manager.choose_model(body.get("model"), messages)
        session_id = request.headers.get("x-session-id")
        if session_id:
            body["messages"] = await session_manager.context(session_id, messages)
        endpoint = await model_manager.get_endpoint(model_name)
        body.setdefault("model", model_name)
        timeout = model_manager.registry.get(model_name).timeout
        if body.get("stream"):
            return StreamingResponse(client.stream(endpoint, body, timeout), media_type="text/event-stream", headers={"X-Model-Route": route, "Cache-Control": "no-cache"})
        response = await client.completion(endpoint, body, timeout)
        if session_id:
            assistant_messages = [choice.get("message") for choice in response.get("choices", []) if choice.get("message")]
            await session_manager.save(session_id, messages + assistant_messages)
        return response
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {error}") from error


@router.get("/models")
async def list_models(request: Request):
    _authorize(request)
    return {"object": "list", "data": [{"id": name, "object": "model", "owned_by": "ai-gateway"} for name in model_manager.registry.names()]}
