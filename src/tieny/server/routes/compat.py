"""Compatibility routes matching the existing prototype API names."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from tieny.schemas.model import AddModelRequest, LoadModelRequest
from tieny.server import state

router = APIRouter(tags=["compatibility"])


@router.get("/models")
def models() -> list[dict]:
    loaded = state.runtime.loaded_model
    output = []
    for model in state.models.list():
        item = model.to_dict()
        item["loaded"] = bool(loaded and loaded.id == model.id)
        try:
            item["size_bytes"] = Path(model.path).stat().st_size
        except OSError:
            item["size_bytes"] = None
        output.append(item)
    return output


@router.post("/models/add")
def add_model(request: AddModelRequest) -> dict:
    return state.models.add(request.path).to_dict()


@router.post("/models/load")
def load_model(request: LoadModelRequest) -> dict:
    return state.runtime.load(request.target).to_dict()
