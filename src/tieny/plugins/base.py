"""Minimal plugin contract scaffold. Optional beta plugins are not implemented yet."""

from __future__ import annotations

from abc import ABC


class BasePlugin(ABC):
    """Marker/base contract that can grow only when real plugin requirements exist."""

    name: str
    beta: bool = True
