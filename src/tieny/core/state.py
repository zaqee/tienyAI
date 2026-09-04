from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from tieny.core.paths import ensure_data_dirs, state_path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TienyState:
    last_used_model: str | None = None


class StateStore:
    """Persist application-managed state separately from user configuration."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_path()

    def load(self) -> TienyState:
        ensure_data_dirs()

        if not self.path.exists():
            state = TienyState()
            self.save(state)
            logger.info("Created default state at %s", self.path)
            return state

        logger.debug("Reading state from %s", self.path)

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read state file; using default state.")
            return TienyState()

        if not isinstance(raw, dict):
            return TienyState()

        allowed = {
            field_name: raw[field_name]
            for field_name in TienyState.__dataclass_fields__
            if field_name in raw
        }

        return TienyState(**allowed)

    def save(self, state: TienyState) -> None:
        ensure_data_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(state), indent=2),
            encoding="utf-8",
        )
        logger.debug("Saved state to %s", self.path)

    def set_last_used_model(self, model: str) -> None:
        state = self.load()
        state.last_used_model = model
        self.save(state)
