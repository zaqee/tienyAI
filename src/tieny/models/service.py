"""Authoritative model-management service shared by Python, CLI, and server."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tieny.core.errors import ModelNameConflictError, ModelNotFoundError, TienyError
from tieny.models.detector import detect_model
from tieny.models.entity import ModelRecord
from tieny.models.registry import ModelRegistry

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or ModelRegistry()

    def list(self) -> list[ModelRecord]:
        models = self.registry.all()
        logger.debug("Listing %d registered model(s)", len(models))
        return models

    def resolve(self, target: str) -> ModelRecord:
        """Resolve a model by exact ID or exact name, never by fuzzy guessing."""
        models = self.registry.all()
        logger.debug("Resolving model target '%s'", target)
        for model in models:
            if model.id == target:
                logger.debug("Resolved '%s' by ID -> %s", target, model.name)
                return model
        for model in models:
            if model.name == target:
                logger.debug("Resolved '%s' by name -> %s", target, model.id)
                return model
        raise ModelNotFoundError(f"No registered model matches ID or name '{target}'.")

    def _unique_name(self, desired: str, *, excluding_id: str | None = None) -> str:
        existing = {
            model.name
            for model in self.registry.all()
            if excluding_id is None or model.id != excluding_id
        }
        if desired not in existing:
            return desired
        index = 1
        while f"{desired}{index}" in existing:
            index += 1
        resolved = f"{desired}{index}"
        logger.debug("Name collision for '%s'; selected '%s'", desired, resolved)
        return resolved

    def add(self, raw_path: str) -> ModelRecord:
        path = Path(raw_path).expanduser().resolve()
        logger.info("Adding model from path %s", path)
        if not path.exists():
            raise TienyError(f"Model file does not exist: {path}")
        if not path.is_file():
            raise TienyError(f"Model path is not a file: {path}")

        models = self.registry.all()
        for model in models:
            if Path(model.path) == path:
                raise TienyError(
                    f"That exact file is already registered as '{model.name}' ({model.id})."
                )

        model_type, model_format, runtime = detect_model(path)
        record = ModelRecord(
            id=uuid.uuid4().hex[:8],
            name=self._unique_name(path.stem),
            type=model_type,
            format=model_format,
            path=str(path),
            runtime=runtime,
            added_at=datetime.now(timezone.utc).isoformat(),
        )
        models.append(record)
        self.registry.replace_all(models)
        logger.info(
            "Registered model id=%s name=%s type=%s runtime=%s path=%s",
            record.id,
            record.name,
            record.type,
            record.runtime,
            record.path,
        )
        return record

    def rename(self, target: str, new_name: str) -> ModelRecord:
        model = self.resolve(target)
        clean = new_name.strip()
        if not clean:
            raise TienyError("Model name cannot be empty.")
        if any(char in clean for char in "\\/\0"):
            raise TienyError("Model name cannot contain path separators or NUL characters.")

        models = self.registry.all()
        if any(item.name == clean and item.id != model.id for item in models):
            raise ModelNameConflictError(f"A model named '{clean}' already exists.")
        for item in models:
            if item.id == model.id:
                old = item.name
                item.name = clean
                self.registry.replace_all(models)
                logger.info("Renamed model %s from '%s' to '%s'", item.id, old, clean)
                return item
        raise ModelNotFoundError(target)

    def reset_name(self, target: str) -> ModelRecord:
        model = self.resolve(target)
        desired = Path(model.path).stem
        unique = self._unique_name(desired, excluding_id=model.id)
        logger.info("Resetting model %s name to filename-derived '%s'", model.id, unique)
        return self.rename(model.id, unique)

    def remove(self, target: str, *, delete_file: bool = False) -> ModelRecord:
        model = self.resolve(target)
        models = [item for item in self.registry.all() if item.id != model.id]

        # Delete first when explicitly requested so a failed filesystem operation does not
        # silently leave an untracked model file behind.
        if delete_file:
            path = Path(model.path)
            logger.warning("Deleting original model file for %s: %s", model.id, path)
            try:
                path.unlink()
            except FileNotFoundError:
                logger.warning("Original model file was already missing: %s", path)
            except OSError as exc:
                logger.exception("Failed to delete model file %s", path)
                raise TienyError(f"Could not delete model file: {exc}") from exc

        self.registry.replace_all(models)
        logger.info(
            "Removed model %s (%s) from registry; delete_file=%s",
            model.id,
            model.name,
            delete_file,
        )
        return model
