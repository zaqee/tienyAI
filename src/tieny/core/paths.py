"""Filesystem locations used by Tieny.

All runtime state lives outside the source tree. ``TIENY_HOME`` can override the
platform default, which also makes tests and portable development setups easy.
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir


def home_dir() -> Path:
    """Return Tieny's writable data directory."""
    override = os.getenv("TIENY_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path(user_data_dir("Tieny", "Tieny")).resolve()


def models_registry_path() -> Path:
    return home_dir() / "models.json"


def config_path() -> Path:
    return home_dir() / "config.json"


def logs_dir() -> Path:
    return home_dir() / "logs"


def log_file_path() -> Path:
    return logs_dir() / "tieny.log"


def ensure_data_dirs() -> None:
    """Create the small set of directories Tieny itself owns."""
    home_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
