"""Deterministic dependency installer for the deliberately tiny v0.2.0 runtime set."""

from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys

from tieny.core.paths import ensure_data_dirs
from tieny.core.errors import TienyError

logger = logging.getLogger(__name__)


class Installer:
    """Install only dependencies Tieny explicitly knows about.

    Future lazy runtime installs belong behind this deterministic layer. The beta
    AI installer must remain separate so unsupported-model experimentation never
    becomes a silent fallback.
    """

    def install(self) -> None:
        ensure_data_dirs()
        logger.info("Starting Tieny dependency installation")

        if importlib.util.find_spec("llama_cpp") is not None:
            logger.info("llama-cpp-python is already installed")
            return

        logger.info("Installing llama-cpp-python for the basic GGUF LLM runtime")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "llama-cpp-python>=0.3"]
            )
        except subprocess.CalledProcessError as exc:
            logger.exception("Dependency installation failed")
            raise TienyError(
                "Failed to install llama-cpp-python. Check the build output above; "
                "prebuilt/runtime-specific install paths are intentionally not part of v0.2.0 yet."
            ) from exc
        logger.info("Tieny dependency installation completed")
