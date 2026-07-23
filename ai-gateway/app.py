from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse

from api.health import router as health_router
from api.images import image_generator, router as images_router, _cleanup_task
from api.openai import router as openai_router
from api.tools import router as tools_router
from managers.model_manager import model_manager


async def _idle_monitor() -> None:
    while True:
        await asyncio.sleep(60)
        await model_manager.unload_if_idle()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Validate configuration before the app starts handling requests.
    model_manager.validate_configuration()
    image_generator.validate_configuration()
    task_idle = asyncio.create_task(_idle_monitor())
    task_cleanup = asyncio.create_task(_cleanup_task())
    try:
        yield
    finally:
        task_idle.cancel()
        task_cleanup.cancel()
        # Await cancellation of both background tasks
        with suppress(asyncio.CancelledError):
            await task_idle
            await task_cleanup
        await model_manager.shutdown()


app = FastAPI(title="AI Gateway", version="1.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------
# Global OpenAI‑style error handler
# ---------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def openai_http_exception_handler(request: Request, exc: HTTPException):
    """Return errors in the OpenAI compatible envelope.

    The gateway previously returned FastAPI's default ``{"detail": ...}``.
    Clients that expect the OpenAI error schema look for an ``error`` object
    containing ``message`` and ``type``.  This handler preserves the original
    status code while wrapping the detail in that structure.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.detail, "type": "invalid_request_error"}},
    )

# ---------------------------------------------------------------------
# Request size limit middleware
# ---------------------------------------------------------------------
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MiB – adjust as needed

@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            size = int(content_length)
        except ValueError:
            size = 0
        if size > MAX_BODY_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Request body too large ({size} bytes). Max allowed is {MAX_BODY_SIZE}.",
            )
    # If header missing, FastAPI will read the body; we cannot easily limit without reading.
    return await call_next(request)
app.include_router(openai_router, prefix="/v1", tags=["OpenAI-compatible API"])
app.include_router(images_router, prefix="/v1/images", tags=["OpenAI-compatible image API"])
app.include_router(health_router, prefix="/health", tags=["Operations"])
app.include_router(tools_router, prefix="/tool", tags=["Local tools"])


@app.get("/")
async def root():
    return {"status": "AI Gateway is running", "docs": "/docs"}
