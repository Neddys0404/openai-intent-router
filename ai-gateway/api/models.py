"""Pydantic request models for the OpenAI‑compatible endpoints.

These models provide strict validation and type hints for the gateway’s
public API.  They are intentionally lightweight – only the fields that are
currently used by the implementation are included.  Additional fields can be
added later without breaking existing clients.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, validator


class Message(BaseModel):
    role: str = Field(..., description="The role of the message sender.")
    content: str = Field(..., description="The textual content of the message.")


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(None, description="Explicit model name or 'auto' for classifier routing.")
    messages: List[Message] = Field(..., min_items=1)
    stream: bool = False
    n: int = 1
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: Optional[int]
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

    @validator("n")
    def _positive_n(cls, v):
        if v <= 0:
            raise ValueError("n must be positive")
        return v


class CompletionRequest(BaseModel):
    model: str = Field(..., description="Explicit model name.")
    prompt: str = Field(..., min_length=1)
    max_tokens: Optional[int]
    temperature: float = 1.0
    top_p: float = 1.0
    n: int = 1
    stream: bool = False

    @validator("n")
    def _positive_n(cls, v):
        if v <= 0:
            raise ValueError("n must be positive")
        return v


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    n: int = 1
    size: str = "1024x1024"
    response_format: str = "b64_json"

    @validator("n")
    def _positive_n(cls, v):
        if v != 1:
            raise ValueError("Only n=1 is supported for image generation.")
        return v