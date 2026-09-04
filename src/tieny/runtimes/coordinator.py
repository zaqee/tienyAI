"""Select and own the currently active runtime/model inside a persistent process."""

from __future__ import annotations

import logging
from typing import Any

from tieny.core.config import ConfigStore
from tieny.core.errors import RuntimeStateError
from tieny.models.entity import ModelRecord
from tieny.models.service import ModelService
from tieny.runtimes.base import BaseRuntime
from tieny.runtimes.registry import RuntimeRegistry

logger = logging.getLogger(__name__)


class RuntimeCoordinator:
    def __init__(
        self,
        models: ModelService | None = None,
        registry: RuntimeRegistry | None = None,
    ) -> None:
        self.models = models or ModelService()
        self.config = ConfigStore().load()
        self.registry = registry or RuntimeRegistry()
        self._runtime: BaseRuntime | None = None
        self._runtime_name: str | None = None
        self._loaded_model: ModelRecord | None = None

    @property
    def loaded_model(self) -> ModelRecord | None:
        return self._loaded_model

    def _runtime_for(self, runtime_name: str) -> BaseRuntime:
        if self._runtime is not None and self._runtime_name == runtime_name:
            return self._runtime
        if self._runtime is not None:
            self._runtime.unload()
        logger.debug("Creating runtime adapter '%s'", runtime_name)
        self._runtime = self.registry.create(runtime_name, self.config)
        self._runtime_name = runtime_name
        return self._runtime

    def load(self, target: str) -> ModelRecord:
        model = self.models.resolve(target)
        logger.debug(
            "Runtime coordinator resolving model %s -> type=%s runtime=%s",
            model.id,
            model.type,
            model.runtime,
        )
        runtime = self._runtime_for(model.runtime)
        runtime.load(model)
        self._loaded_model = model
        return model

    def unload(self, target: str | None = None) -> ModelRecord | None:
        loaded = self._loaded_model
        if loaded is None:
            logger.info("Runtime coordinator received unload with no loaded model")
            return None
        if target is not None:
            requested = self.models.resolve(target)
            if requested.id != loaded.id:
                raise RuntimeStateError(
                    f"'{requested.name}' is not loaded. Current model is '{loaded.name}'."
                )
        if self._runtime is not None:
            self._runtime.unload()
        self._loaded_model = None
        return loaded

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        if self._loaded_model is None or self._runtime is None:
            raise RuntimeStateError("No model is loaded.")
        chat = getattr(self._runtime, "chat", None)
        if chat is None:
            raise RuntimeStateError(
                f"Runtime '{self._runtime_name}' does not expose chat capability."
            )
        return chat(messages, max_tokens=max_tokens, temperature=temperature)
