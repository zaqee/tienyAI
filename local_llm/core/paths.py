"""Centralized filesystem paths.

Keeping all app paths here makes the project easier to maintain,
debug, and migrate later.
"""
from __future__ import annotations

from pathlib import Path

APP_DIR = Path.home() / ".local-llm"
MODELS_DIR = APP_DIR / "models"
LOGS_DIR = APP_DIR / "logs"
REGISTRY_PATH = APP_DIR / "registry.toml"
CONFIG_PATH = APP_DIR / "config.toml"


def ensure_app_dirs() -> None:
    """Create the app directories if they do not already exist."""
    for path in (APP_DIR, MODELS_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)
