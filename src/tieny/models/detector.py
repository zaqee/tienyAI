"""Model detection boundary.

v0.2.0 intentionally recognizes only GGUF LLM files. The return shape is already
modality/runtime aware so STT/TTS/IMG detection can be added without changing the
registry or generic CLI commands.
"""

from __future__ import annotations

from pathlib import Path

from tieny.core.errors import TienyError


class UnsupportedModelError(TienyError):
    pass


def detect_model(path: Path) -> tuple[str, str, str]:
    suffix = path.suffix.lower()
    if suffix == ".gguf":
        return "llm", "gguf", "llama.cpp"
    raise UnsupportedModelError(
        f"Unsupported model format '{suffix or '<none>'}'. v0.2.0 only wires GGUF LLM models."
    )
