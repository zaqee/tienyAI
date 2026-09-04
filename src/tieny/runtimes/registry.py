"""Runtime factory registry.

Keeping runtime selection behind this tiny registry means future Whisper/TTS/image
backends can register here without teaching generic model commands about them.
"""

from __future__ import annotations

from collections.abc import Callable

from tieny.core.config import TienyConfig
from tieny.core.errors import RuntimeUnavailableError
from tieny.runtimes.base import BaseRuntime
from tieny.runtimes.llama_cpp import LlamaCppRuntime

RuntimeFactory = Callable[[TienyConfig], BaseRuntime]


class RuntimeRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, RuntimeFactory] = {
            "llama.cpp": LlamaCppRuntime,
        }

    def register(self, name: str, factory: RuntimeFactory) -> None:
        self._factories[name] = factory

    def create(self, name: str, config: TienyConfig) -> BaseRuntime:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise RuntimeUnavailableError(
                f"Runtime '{name}' is not registered in this Tieny build."
            ) from exc
        return factory(config)

    def names(self) -> tuple[str, ...]:
        return tuple(self._factories)
