from __future__ import annotations

from pydantic import BaseModel, Field


class AddModelRequest(BaseModel):
    path: str


class LoadModelRequest(BaseModel):
    target: str


class RenameModelRequest(BaseModel):
    name: str | None = None
    remove: bool = False


class ModelResponse(BaseModel):
    id: str
    name: str
    type: str
    format: str
    path: str
    runtime: str
    added_at: str
    loaded: bool = False
    size_bytes: int | None = None


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int = Field(default=256, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
