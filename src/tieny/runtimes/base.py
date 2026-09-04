"""Runtime contract for concrete model execution backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from tieny.models.entity import ModelRecord


class BaseRuntime(ABC):
    """Small lifecycle contract shared by future runtimes."""

    name: str

    @abstractmethod
    def load(self, model: ModelRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def loaded_model_id(self) -> str | None:
        raise NotImplementedError
