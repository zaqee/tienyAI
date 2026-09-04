"""Public Python API. Developers can embed Tieny without going through HTTP/CLI."""

from __future__ import annotations

from tieny.core.config import ConfigStore
from tieny.core.logging import setup_logging
from tieny.models import ModelRecord, ModelService
from tieny.runtimes import RuntimeCoordinator

setup_logging(ConfigStore().load().log_level)

_models = ModelService()
_runtime = RuntimeCoordinator(_models)


def add(path: str) -> ModelRecord:
    return _models.add(path)


def list_models() -> list[ModelRecord]:
    return _models.list()


def load(target: str) -> ModelRecord:
    """Load into this Python process."""
    return _runtime.load(target)


def unload(target: str | None = None) -> ModelRecord | None:
    return _runtime.unload(target)


def remove(target: str, *, delete_file: bool = False) -> ModelRecord:
    loaded = _runtime.loaded_model
    model = _models.resolve(target)
    if loaded and loaded.id == model.id:
        _runtime.unload(model.id)
    return _models.remove(model.id, delete_file=delete_file)


def name(target: str, new_name: str | None = None, *, remove: bool = False) -> ModelRecord:
    if remove:
        return _models.reset_name(target)
    if new_name is None:
        raise ValueError("new_name is required unless remove=True")
    return _models.rename(target, new_name)


def chat(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> dict:
    return _runtime.chat(messages, max_tokens=max_tokens, temperature=temperature)
