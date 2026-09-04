"""Small JSON configuration layer for core/server settings."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tieny.core.paths import config_path, ensure_data_dirs

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PreloadConfig:
    # None means: use the last successfully loaded model.
    model: str | None = None
    auto: bool = False


@dataclass(slots=True)
class UiConfig:
    auto_open: bool = True


@dataclass(slots=True)
class TienyConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "DEBUG"
    n_ctx: int = 2048
    n_gpu_layers: int = 0

    preload: PreloadConfig = field(default_factory=PreloadConfig)
    ui: UiConfig = field(default_factory=UiConfig)


class ConfigStore:
    """Persist user configuration without mixing it with application state."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_path()

    def load(self) -> TienyConfig:
        ensure_data_dirs()

        if not self.path.exists():
            config = TienyConfig()
            self.save(config)
            logger.info("Created default config at %s", self.path)
            return config

        logger.debug("Reading config from %s", self.path)
        raw = json.loads(self.path.read_text(encoding="utf-8"))

        preload_raw = raw.get("preload", {})
        if not isinstance(preload_raw, dict):
            preload_raw = {}

        preload = PreloadConfig(
            model=preload_raw.get("model"),
            auto=preload_raw.get("auto", False),
        )

        ui_raw = raw.get("ui", {})
        if not isinstance(ui_raw, dict):
            ui_raw = {}

        ui = UiConfig(
            auto_open=ui_raw.get("auto_open", True),
        )

        allowed = {
            field_name: raw[field_name]
            for field_name in TienyConfig.__dataclass_fields__
            if field_name in raw and field_name not in {"preload", "ui"}
        }

        return TienyConfig(
            **allowed,
            preload=preload,
            ui=ui,
        )

    def save(self, config: TienyConfig) -> None:
        ensure_data_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(config), indent=2),
            encoding="utf-8",
        )
        logger.debug("Saved config to %s", self.path)
