"""Inference helpers around llama-cpp-python."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from .registry import ModelEntry, default_registry


@dataclass
class RuntimeState:
    """In-memory state for the running server process."""

    active_model: ModelEntry | None = None
    llm: Any | None = None
    settings: dict[str, Any] = field(default_factory=lambda: default_registry()["settings"].copy())
    lock: Lock = field(default_factory=Lock)

    def load_model(self, model: ModelEntry) -> None:
        """Load a GGUF model using llama.cpp."""
        with self.lock:
            self.active_model = model
            self.llm = self._create_llm(Path(model.local_path))

    def _create_llm(self, model_path: Path):
        # Import lazily so the rest of the app can still start and show
        # helpful errors if the llama_cpp package is missing.
        try:
            from llama_cpp import Llama
        except Exception as exc:  # pragma: no cover - import error path
            raise RuntimeError(
                "llama-cpp-python is not installed. Install dependencies and try again."
            ) from exc

        if not model_path.exists():
            raise FileNotFoundError(f"Loaded model file does not exist: {model_path}")

        return Llama(
            model_path=str(model_path),
            n_ctx=int(self.settings.get("n_ctx", 4096)),
            verbose=False,
        )

    def update_settings(self, **kwargs: Any) -> None:
        with self.lock:
            for key, value in kwargs.items():
                if value is not None:
                    self.settings[key] = value

    def _complete(self, prompt: str, *, temperature: float | None = None, max_tokens: int | None = None) -> str:
        if self.llm is None:
            raise RuntimeError("No model is loaded.")

        result = self.llm(
            prompt,
            max_tokens=int(max_tokens or self.settings.get("max_tokens", 256)),
            temperature=float(temperature if temperature is not None else self.settings.get("temperature", 0.7)),
            top_p=float(self.settings.get("top_p", 0.95)),
            repeat_penalty=float(self.settings.get("repeat_penalty", 1.1)),
            stop=["User:"],
        )
        text = result["choices"][0]["text"].strip()
        return text or "I did not generate a response."

    def generate(self, message: str, *, temperature: float | None = None, max_tokens: int | None = None) -> str:
        """Run a plain text completion prompt."""
        with self.lock:
            prompt = (
                "You are a helpful local assistant.\n\n"
                f"User: {message}\n"
                "Assistant:"
            )
            return self._complete(prompt, temperature=temperature, max_tokens=max_tokens)

    def generate_chat(self, messages: list[dict[str, str]], *, temperature: float | None = None, max_tokens: int | None = None) -> str:
        with self.lock:
            conversation = []
            for msg in messages:
                role = msg.get("role", "user").lower()
                content = msg.get("content", "")
                if role == "system":
                    conversation.append(f"System: {content}")
                elif role == "assistant":
                    conversation.append(f"Assistant: {content}")
                else:
                    conversation.append(f"User: {content}")

            conversation.append("Assistant:")
            prompt = "\n".join(conversation)
            return self._complete(prompt, temperature=temperature, max_tokens=max_tokens)
