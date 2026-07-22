from __future__ import annotations

import asyncio
import json
from pathlib import Path
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
session_directory = Path(gateway_config.get("session_directory", "sessions"))
if not session_directory.is_absolute():
    session_directory = Path(__file__).parents[1] / session_directory
session_manager = SessionManager(str(session_directory), gateway_config.get("max_recent_messages", 20))


def _authorize(request: Request) -> None:
    api_key = gateway_config.get("api_key")
    if api_key and request.headers.get("authorization") != f"Bearer {api_key}":
        raise HTTPException(status_code=401, detail="Invalid API key")


def _stream_content(chunk: bytes, buffer: bytes) -> tuple[bytes, list[str], bool]:
    buffer += chunk
    content: list[str] = []
    complete = False
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        payload = line.strip().removeprefix(b"data:").strip()
        if not line.strip().startswith(b"data:"):
            continue
        if payload == b"[DONE]":
            complete = True
            continue
        try:
            delta = json.loads(payload).get("choices", [{}])[0].get("delta", {})
            if isinstance(delta.get("content"), str):
                content.append(delta["content"])
        except (json.JSONDecodeError, IndexError, TypeError, AttributeError):
            continue
    return buffer, content, complete


async def _stream_response(
    endpoint: str,
    body: dict[str, Any],
    timeout: float,
    session_id: str | None,
    original_messages: list[dict[str, Any]],
    model_name: str,
):
    buffer = b""
    parts: list[str] = []
    completed = False
    try:
        async for chunk in client.stream(endpoint, body, timeout):
            buffer, content, done = _stream_content(chunk, buffer)
            parts.extend(content)
            completed = completed or done
            yield chunk
    finally:
        try:
            if session_id and completed:
                await session_manager.save(session_id, original_messages + [{"role": "assistant", "content": "".join(parts)}])
        finally:
            model_manager.release_request(model_name)


async def _stream_text_completion_response(
    endpoint: str, body: dict[str, Any], timeout: float, model_name: str
):
    try:
        async for chunk in client.stream_text_completion(endpoint, body, timeout):
            yield chunk
    finally:
        model_manager.release_request(model_name)


@router.post("/chat/completions")
async def chat_completions(request: Request):
    _authorize(request)
    try:
        body: dict[str, Any] = await request.json()
        original_messages = body.get("messages")
        if not isinstance(original_messages, list) or not original_messages:
            raise ValueError("'messages' must be a non-empty list.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    await model_manager.acquire_request()
    streaming = False
    model_name: str | None = None
    try:
        session_id = request.headers.get("x-session-id")
        if session_id:
            body["messages"] = await session_manager.context(session_id, original_messages)
        routing_messages = body["messages"]
        if not body.get("model") or body.get("model") in {"auto", "gateway"}:
            await model_manager.get_endpoint(router_manager.classifier_model)
        model_name, route = await router_manager.choose_model(body.get("model"), routing_messages)
        endpoint = await model_manager.get_endpoint(model_name)
        body["model"] = model_name
        timeout = model_manager.registry.get(model_name).timeout
        if body.get("stream"):
            streaming = True
            return StreamingResponse(
                _stream_response(endpoint, body, timeout, session_id, original_messages, model_name),
                media_type="text/event-stream",
                headers={"X-Model-Route": route, "Cache-Control": "no-cache"},
            )
        response = await client.completion(endpoint, body, timeout)
        if session_id:
            assistant_messages = [choice.get("message") for choice in response.get("choices", []) if choice.get("message")]
            await session_manager.save(session_id, original_messages + assistant_messages)
        return response
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {error}") from error
    finally:
        if not streaming:
            model_manager.release_request(model_name)


@router.post("/completions")
async def completions(request: Request):
    """Proxy the OpenAI text-completions API used by editor autocomplete clients.

    Text completions have no chat messages to classify, so callers must select a
    configured model explicitly (for example, ``model: \"coder\"``).
    """
    _authorize(request)
    try:
        body: dict[str, Any] = await request.json()
        if "prompt" not in body:
            raise ValueError("'prompt' is required for text completions.")
        model_name = body.get("model")
        if not isinstance(model_name, str) or not model_name or model_name in {"auto", "gateway"}:
            raise ValueError("Text completions require an explicit configured model (for example, 'coder').")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    await model_manager.acquire_request()
    streaming = False
    try:
        endpoint = await model_manager.get_endpoint(model_name)
        timeout = model_manager.registry.get(model_name).timeout
        if body.get("stream"):
            streaming = True
            return StreamingResponse(
                _stream_text_completion_response(endpoint, body, timeout, model_name),
                media_type="text/event-stream",
                headers={"X-Model-Route": "explicit", "Cache-Control": "no-cache"},
            )
        return await client.text_completion(endpoint, body, timeout)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {error}") from error
    finally:
        if not streaming:
            model_manager.release_request(model_name)


@router.get("/models")
async def list_models(request: Request):
    _authorize(request)
    models = [
        {"id": name, "object": "model", "owned_by": "ai-gateway"}
        for name in model_manager.registry.names()
        if name != router_manager.classifier_model
    ]
    image_config = model_manager.config.get("image_generation", {})
    image_model = image_config.get("model")
    image_ids = [image_model]
    aliases = image_config.get("aliases", [])
    if isinstance(aliases, list):
        image_ids.extend(aliases)
    if image_config.get("enabled"):
        for image_id in image_ids:
            if isinstance(image_id, str) and image_id and not any(model["id"] == image_id for model in models):
                models.append({"id": image_id, "object": "model", "owned_by": "ai-gateway-image"})
    return {"object": "list", "data": models}
