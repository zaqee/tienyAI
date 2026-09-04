"""Unified model record used by every modality."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ModelRecord:
    id: str
    name: str
    type: str
    format: str
    path: str
    runtime: str
    added_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ModelRecord":
        return cls(**data)
