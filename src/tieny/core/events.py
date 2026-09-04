"""Tiny event hook scaffold.

This intentionally does not attempt to be a full plugin event bus yet. It gives
future modules/plugins a clear architectural home without dragging beta features
into the v0.2.0 implementation.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def on(self, event: str, handler: Callable[..., None]) -> None:
        self._handlers[event].append(handler)

    def emit(self, event: str, **payload: object) -> None:
        for handler in tuple(self._handlers.get(event, ())):
            handler(**payload)
