from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from api.health import router as health_router
from api.openai import router as openai_router
from api.tools import router as tools_router
from managers.model_manager import model_manager


async def _idle_monitor() -> None:
    while True:
        await asyncio.sleep(60)
        await model_manager.unload_if_idle()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_idle_monitor())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="AI Gateway", version="1.0.0", lifespan=lifespan)
app.include_router(openai_router, prefix="/v1", tags=["OpenAI-compatible API"])
app.include_router(health_router, prefix="/health", tags=["Operations"])
app.include_router(tools_router, prefix="/tool", tags=["Local tools"])


@app.get("/")
async def root():
    return {"status": "AI Gateway is running", "docs": "/docs"}
