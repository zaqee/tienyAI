"""Basic chat route plus the existing OpenAI-style compatibility endpoint."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter

from tieny.schemas.model import ChatRequest
from tieny.server import state

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def _messages(request: ChatRequest) -> list[dict[str, str]]:
    return [message.model_dump() for message in request.messages]


@router.post("/api/chat")
def api_chat(request: ChatRequest) -> dict:
    logger.info("HTTP /api/chat messages=%d", len(request.messages))
    return state.runtime.chat(
        _messages(request),
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )


@router.post("/chat")
def legacy_chat(request: ChatRequest) -> dict:
    """Keep the existing simple /chat route available during the rewrite."""
    logger.info("HTTP compatibility /chat messages=%d", len(request.messages))
    return state.runtime.chat(
        _messages(request),
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )


@router.post("/v1/chat/completions")
def openai_chat(request: ChatRequest) -> dict:
    """Small OpenAI-compatible response shape for non-streaming chat completions."""
    logger.info("HTTP OpenAI-compatible chat completion")
    raw = state.runtime.chat(
        _messages(request),
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )
    choice = raw.get("choices", [{}])[0]
    message = choice.get("message", {"role": "assistant", "content": choice.get("text", "")})
    usage = raw.get("usage", {})
    model = state.runtime.loaded_model
    return {
        "id": raw.get("id", f"chatcmpl-{uuid.uuid4().hex[:16]}"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model.name if model else "unknown",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": choice.get("finish_reason", "stop"),
            }
        ],
        "usage": usage,
    }
