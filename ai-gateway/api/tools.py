from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
import asyncio
import subprocess
from pydantic import BaseModel

from managers.model_manager import model_manager
from tools.tool_router import ToolRouter
from .auth import authorize

router = APIRouter()
tool_router = ToolRouter(model_manager.config.get("tools", {}))


class ToolRequest(BaseModel):
    command: str


@router.post("/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest, raw_request: Request):
    authorize(raw_request)
    try:
        return await asyncio.to_thread(tool_router.execute, tool_name, request.command)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except subprocess.TimeoutExpired as error:
        raise HTTPException(status_code=504, detail=f"Tool timed out after {error.timeout} seconds.") from error
