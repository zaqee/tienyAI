"""
Model intake:
- local file path
- direct URL download
- automatic registry registration
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, unquote
from urllib.request import urlopen
from typing import Any
from datetime import datetime, timezone

from .paths import MODELS_DIR, ensure_app_dirs
from .registry import (
    ModelEntry,
    asdict,
    load_registry,
    save_registry,
    next_model_id,
    copy_local_model_into_store,
    utc_now_iso,
)


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def guess_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if not name:
        return "model.gguf"
    return name


def download_url_to_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, open(destination, "wb") as out_file:
        out_file.write(response.read())


def register_model_from_local_path(path_text: str) -> ModelEntry:
    source_path = Path(path_text).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Model file not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Model path is not a file: {source_path}")

    data = load_registry()
    existing = data.get("models", [])
    model_id = next_model_id(len(existing))

    copied_path = copy_local_model_into_store(source_path, model_id)

    entry = ModelEntry(
        id=model_id,
        name=source_path.stem,
        local_path=str(copied_path),
        source_type="local",
        source=str(source_path),
        added_at=utc_now_iso(),
    )

    data.setdefault("models", [])
    data["models"].append(asdict(entry))
    data.setdefault("app", {})
    data["app"]["active_model_id"] = model_id
    save_registry(data)
    return entry


def register_model_from_url(url: str) -> ModelEntry:
    if not is_url(url):
        raise ValueError("URL must start with http:// or https://")

    data = load_registry()
    existing = data.get("models", [])
    model_id = next_model_id(len(existing))

    filename = guess_filename_from_url(url)
    if not filename.lower().endswith(".gguf"):
        # Keep the user's filename, but make the extension obvious if missing.
        filename = f"{Path(filename).stem}.gguf"

    target_dir = MODELS_DIR / model_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename

    download_url_to_file(url, target_file)

    entry = ModelEntry(
        id=model_id,
        name=Path(filename).stem,
        local_path=str(target_file),
        source_type="url",
        source=url,
        added_at=utc_now_iso(),
    )

    data.setdefault("models", [])
    data["models"].append(asdict(entry))
    data.setdefault("app", {})
    data["app"]["active_model_id"] = model_id
    save_registry(data)
    return entry