"""Minimal module boundary for future LLM/STT/TTS/IMG capabilities."""

from __future__ import annotations

from abc import ABC


class BaseModule(ABC):
    kind: str
