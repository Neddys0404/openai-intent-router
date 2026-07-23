from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from managers.model_manager import model_manager


def authorize(request: Request) -> None:
    gateway_config = model_manager.config.get("gateway", {})
    api_key = gateway_config.get("api_key")
    authorization = request.headers.get("authorization", "")
    expected = f"Bearer {api_key}" if isinstance(api_key, str) else ""
    if api_key and not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")
