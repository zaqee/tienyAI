"""Canonical model-management API routes used by the Web UI."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter

from tieny.schemas.model import AddModelRequest, ModelResponse, RenameModelRequest
from tieny.server import state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])


def _response(model) -> ModelResponse:
    path = Path(model.path)
    try:
        size = path.stat().st_size
    except OSError:
        size = None
    loaded = bool(state.runtime.loaded_model and state.runtime.loaded_model.id == model.id)
    return ModelResponse(**model.to_dict(), loaded=loaded, size_bytes=size)


@router.get("")
def list_models() -> list[ModelResponse]:
    logger.debug("HTTP list models")
    return [_response(model) for model in state.models.list()]


@router.post("/add")
def add_model(request: AddModelRequest) -> ModelResponse:
    logger.info("HTTP add model request: %s", request.path)
    return _response(state.models.add(request.path))


@router.post("/load/{target}")
def load_model(target: str) -> ModelResponse:
    logger.info("HTTP load model target=%s", target)
    return _response(state.runtime.load(target))


@router.post("/unload")
def unload_model(target: str | None = None) -> dict:
    logger.info("HTTP unload model target=%s", target)
    model = state.runtime.unload(target)
    return {"unloaded": model.to_dict() if model else None}


@router.post("/{target}/name")
def rename_model(target: str, request: RenameModelRequest) -> ModelResponse:
    logger.info("HTTP name model target=%s remove=%s", target, request.remove)
    if request.remove:
        model = state.models.reset_name(target)
    else:
        if request.name is None:
            raise ValueError("name is required when remove=false")
        model = state.models.rename(target, request.name)
    return _response(model)


@router.delete("/{target}")
def remove_model(target: str, delete_file: bool = False) -> dict:
    logger.warning("HTTP remove model target=%s delete_file=%s", target, delete_file)
    model = state.models.resolve(target)
    if state.runtime.loaded_model and state.runtime.loaded_model.id == model.id:
        state.runtime.unload(model.id)
    removed = state.models.remove(model.id, delete_file=delete_file)
    return {"removed": removed.to_dict(), "deleted_file": delete_file}
