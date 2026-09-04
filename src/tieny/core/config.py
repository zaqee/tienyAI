"""Small JSON configuration layer for core/server settings."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from tieny.core.paths import config_path, ensure_data_dirs

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TienyConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "DEBUG"
    n_ctx: int = 2048
    n_gpu_layers: int = 0


class ConfigStore:
    """Persist core configuration without mixing it with browser-only UI state."""

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
        allowed = {field: raw[field] for field in TienyConfig.__dataclass_fields__ if field in raw}
        return TienyConfig(**allowed)

    def save(self, config: TienyConfig) -> None:
        ensure_data_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
        logger.debug("Saved config to %s", self.path)
