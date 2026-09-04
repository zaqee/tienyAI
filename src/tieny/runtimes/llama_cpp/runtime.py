"""The one real runtime wired in v0.2.0: llama.cpp via llama-cpp-python."""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Any

from tieny.core.config import TienyConfig
from tieny.core.errors import RuntimeStateError, RuntimeUnavailableError, TienyError
from tieny.models.entity import ModelRecord
from tieny.runtimes.base import BaseRuntime

logger = logging.getLogger(__name__)


class LlamaCppRuntime(BaseRuntime):
    name = "llama.cpp"

    def __init__(self, config: TienyConfig) -> None:
        self.config = config
        self._llm: Any | None = None
        self._loaded_model: ModelRecord | None = None

    @property
    def loaded_model_id(self) -> str | None:
        return self._loaded_model.id if self._loaded_model else None

    @property
    def loaded_model(self) -> ModelRecord | None:
        return self._loaded_model

    @staticmethod
    def _llama_class() -> Any:
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise RuntimeUnavailableError(
                "llama-cpp-python is not installed. Run 'tieny install' first."
            ) from exc
        return Llama

    def load(self, model: ModelRecord) -> None:
        if model.type != "llm" or model.format != "gguf":
            raise TienyError(
                f"llama.cpp runtime cannot load type={model.type} format={model.format}."
            )
        path = Path(model.path)
        if not path.exists():
            raise TienyError(f"Registered model file is missing: {path}")

        if self._loaded_model and self._loaded_model.id == model.id:
            logger.info("Model %s (%s) is already loaded", model.id, model.name)
            return
        if self._llm is not None:
            logger.info("Unloading current model before switching to %s", model.name)
            self.unload()

        Llama = self._llama_class()
        logger.info(
            "Loading GGUF model %s (%s) with n_ctx=%s n_gpu_layers=%s",
            model.name,
            model.id,
            self.config.n_ctx,
            self.config.n_gpu_layers,
        )
        try:
            self._llm = Llama(
                model_path=str(path),
                n_ctx=self.config.n_ctx,
                n_gpu_layers=self.config.n_gpu_layers,
                verbose=False,
            )
            self._loaded_model = model
            logger.info("Model loaded successfully: %s (%s)", model.name, model.id)
        except Exception:
            self._llm = None
            self._loaded_model = None
            logger.exception("llama.cpp failed to load model %s", model.path)
            raise

    def unload(self) -> None:
        if self._llm is None:
            logger.info("Unload requested while no model is loaded")
            self._loaded_model = None
            return
        old = self._loaded_model
        logger.info("Unloading model %s", old.name if old else "<unknown>")
        self._llm = None
        self._loaded_model = None
        gc.collect()
        logger.info("Model unloaded")

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        if self._llm is None or self._loaded_model is None:
            raise RuntimeStateError("No model is loaded.")
        logger.info(
            "Generating chat completion with %s; messages=%d max_tokens=%d temperature=%.2f",
            self._loaded_model.name,
            len(messages),
            max_tokens,
            temperature,
        )
        try:
            result = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            logger.debug("Chat completion finished successfully")
            return result
        except Exception:
            logger.exception("Chat completion failed")
            raise
