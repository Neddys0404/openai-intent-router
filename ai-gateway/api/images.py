from __future__ import annotations

import asyncio
import base64
import time
from pathlib import Path
from typing import TextIO

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from managers.model_manager import model_manager
from tools.image_tools import ImageGenerator
from .openai import _authorize

router = APIRouter()
image_generator = ImageGenerator(model_manager.config.get("image_generation", {}))


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    n: int = 1
    size: str = "1024x1024"
    response_format: str = "b64_json"


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(asyncio.shield(process.wait()), timeout=10)
    except TimeoutError:
        process.kill()
        await asyncio.shield(process.wait())


@router.post("/generations")
async def create_image(request: ImageGenerationRequest, raw_request: Request):
    _authorize(raw_request)
    if request.n != 1:
        raise HTTPException(status_code=400, detail="Only n=1 is supported.")
    if request.response_format not in {"url", "b64_json"}:
        raise HTTPException(status_code=400, detail="response_format must be 'url' or 'b64_json'.")

    process: asyncio.subprocess.Process | None = None
    log: TextIO | None = None
    output_file: Path | None = None
    await model_manager.acquire_request()
    try:
        # The diffusion runtime shares GPU resources with managed answer models.
        await model_manager.unload_nonpersistent_models()
        job = image_generator.prepare(request.prompt, request.size)
        output_file = job.output_file
        log = job.log_file.open("w", encoding="utf-8")
        log.write(f"Started: {time.time()}\nOutput: {job.output_file}\n\n")
        process = await asyncio.create_subprocess_exec(
            *job.command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=log,
            stderr=asyncio.subprocess.STDOUT,
            env=job.environment,
        )
        try:
            await asyncio.wait_for(process.wait(), timeout=job.timeout_seconds)
        except TimeoutError as error:
            await _stop_process(process)
            raise HTTPException(status_code=504, detail="Image generation timed out.") from error
        if process.returncode:
            raise RuntimeError(f"Image generation failed with exit code {process.returncode}. See {job.log_file}.")
        if not output_file.is_file():
            raise RuntimeError(f"Image generator exited successfully but did not create {output_file}.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=502, detail=f"Unable to start image generator: {error}") from error
    finally:
        if process is not None:
            await _stop_process(process)
        if log is not None:
            log.write(f"\nFinished: {time.time()}\nExit Code: {process.returncode if process else 'not started'}\n")
            log.close()
        model_manager.release_request()

    if request.response_format == "b64_json":
        assert output_file is not None
        encoded_image = base64.b64encode(output_file.read_bytes()).decode("ascii")
        return {"created": int(time.time()), "data": [{"b64_json": encoded_image}]}
    assert output_file is not None
    image_url = f"{str(raw_request.base_url).rstrip('/')}/v1/images/{output_file.name}"
    return {"created": int(time.time()), "data": [{"url": image_url}]}


@router.get("/{image_name}")
async def get_image(image_name: str, request: Request):
    _authorize(request)
    if Path(image_name).name != image_name or not image_name.endswith(".png"):
        raise HTTPException(status_code=404, detail="Image not found.")
    output_file = image_generator.output_directory() / image_name
    if not output_file.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(output_file, media_type="image/png", filename=image_name)
