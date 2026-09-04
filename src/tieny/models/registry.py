"""Single JSON registry for all current and future model modalities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tieny.core.paths import ensure_data_dirs, models_registry_path
from tieny.models.entity import ModelRecord

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or models_registry_path()

    def _read(self) -> list[ModelRecord]:
        ensure_data_dirs()
        if not self.path.exists():
            self._write([])
            logger.info("Created empty model registry at %s", self.path)
            return []
        logger.debug("Reading model registry from %s", self.path)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        records = [ModelRecord.from_dict(item) for item in raw.get("models", [])]
        logger.debug("Registry contains %d model(s)", len(records))
        return records

    def _write(self, models: list[ModelRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"models": [model.to_dict() for model in models]}
        # Replace atomically so an interrupted write is much less likely to corrupt
        # the registry. This matters because every model modality will share this file.
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        logger.debug("Wrote %d model(s) to registry %s", len(models), self.path)

    def all(self) -> list[ModelRecord]:
        return self._read()

    def replace_all(self, models: list[ModelRecord]) -> None:
        self._write(models)
