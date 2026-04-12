"""TOML-backed registry for models and app settings."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tomlkit import aot, document, dump, parse, table

from .paths import CONFIG_PATH, REGISTRY_PATH, ensure_app_dirs


@dataclass
class ModelEntry:
    """One registered model, whether it came from a path or a URL."""

    id: str
    name: str
    source_type: str  # "path", "url", or "local"
    source: str
    local_path: str
    added_at: str
    alias: str | None = None

    @property
    def path(self) -> Path:
        return Path(self.local_path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_registry() -> dict[str, Any]:
    return {
        "app": {"active_model_id": ""},
        "settings": {
            "temperature": 0.7,
            "max_tokens": 256,
            "top_p": 0.95,
            "repeat_penalty": 1.1,
            "n_ctx": 4096,
        },
        "models": [],
    }


def default_config() -> dict[str, Any]:
    return {
        "ui": {"open_browser": True},
        "server": {"host": "127.0.0.1", "port": 8000},
    }


def _tomlkit_to_plain(value: Any, fallback: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _tomlkit_to_plain(v, fallback.get(k) if isinstance(fallback, dict) else None)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            _tomlkit_to_plain(item, fallback[0] if isinstance(fallback, list) and fallback else None)
            for item in value
        ]
    return value


def _load_toml(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        with path.open("rb") as f:
            data = parse(f.read().decode("utf-8"))
        return _tomlkit_to_plain(data, fallback)
    except Exception:
        return fallback


def _normalize_model(item: dict[str, Any]) -> dict[str, Any]:
    local_path = item.get("local_path") or item.get("path") or ""
    name = str(item.get("name", "model"))

    raw_alias = item.get("alias") or name

    alias = raw_alias.split("/")[-1]                                    # remove URL/path
    alias = alias.split("\\")[-1]                                       # windows paths
    alias = alias.split(".gguf")[0]                                     # remove extension
    alias = alias.split(".Q")[0]                                        # remove quantization suffixes like .Q4_0
    alias = alias.replace("-ggml", "").replace("-GGUF", "")             
    alias = alias.strip()
    
    return {
        "id": str(item.get("id", "")),
        "name": name,
        "source_type": str(item.get("source_type", "local")),
        "source": str(item.get("source", local_path)),
        "local_path": str(local_path),
        "added_at": str(item.get("added_at", _utc_now())),
        "alias": alias,
    }


def load_registry() -> dict[str, Any]:
    ensure_app_dirs()
    data = _load_toml(REGISTRY_PATH, default_registry())

    data.setdefault("app", {}).setdefault("active_model_id", "")
    data.setdefault("settings", {})
    data.setdefault("models", [])

    for key, value in default_registry()["settings"].items():
        data["settings"].setdefault(key, value)

    return data


def save_registry(data: dict[str, Any]) -> None:
    ensure_app_dirs()
    doc = document()

    app_table = table()
    app_table.add("active_model_id", data.get("app", {}).get("active_model_id", ""))
    doc["app"] = app_table

    settings_table = table()
    settings = data.get("settings", {})
    for key in ("temperature", "max_tokens", "top_p", "repeat_penalty", "n_ctx"):
        settings_table.add(key, settings.get(key, default_registry()["settings"][key]))
    doc["settings"] = settings_table

    models_array = aot()
    for item in data.get("models", []):
        model_table = table()
        normalized = _normalize_model(item)

        for field in ("id", "alias", "name", "source_type", "source", "local_path", "added_at"):
            value = normalized.get(field)
            if value is None:
                continue
            model_table.add(field, value)

        models_array.append(model_table)

    doc["models"] = models_array

    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        dump(doc, f)


def load_config() -> dict[str, Any]:
    ensure_app_dirs()
    data = _load_toml(CONFIG_PATH, default_config())

    data.setdefault("ui", {}).setdefault("open_browser", True)
    data.setdefault("server", {})
    data["server"].setdefault("host", "127.0.0.1")
    data["server"].setdefault("port", 8000)

    return data


def save_config(data: dict[str, Any]) -> None:
    ensure_app_dirs()
    doc = document()

    ui_table = table()
    ui_table.add("open_browser", bool(data.get("ui", {}).get("open_browser", True)))
    doc["ui"] = ui_table

    server_table = table()
    server_table.add("host", data.get("server", {}).get("host", "127.0.0.1"))
    server_table.add("port", int(data.get("server", {}).get("port", 8000)))
    doc["server"] = server_table

    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        dump(doc, f)


def get_models(data: dict[str, Any]) -> list[ModelEntry]:
    models = []
    for item in data.get("models", []):
        if isinstance(item, dict):
            models.append(ModelEntry(**_normalize_model(item)))
    return models


def find_model(data: dict[str, Any], model_id: str) -> ModelEntry | None:
    for item in get_models(data):
        if item.id == model_id:
            return item
    return None


def register_model(
    *,
    data: dict[str, Any],
    name: str,
    source_type: str,
    source: str,
    local_path: Path,
    alias: str | None = None,
) -> ModelEntry:
    """Add a model to the registry and make it active."""
    model_id = f"model_{len(data.get('models', [])) + 1:04d}_{int(datetime.now(timezone.utc).timestamp())}"
    entry = ModelEntry(
        id=model_id,
        name=name,
        source_type=source_type,
        source=source,
        local_path=str(local_path),
        added_at=_utc_now(),
        alias=alias,
    )
    data.setdefault("models", []).append(asdict(entry))
    data.setdefault("app", {})["active_model_id"] = entry.id
    return entry


def set_active_model(data: dict[str, Any], model_id: str) -> None:
    data.setdefault("app", {})["active_model_id"] = model_id


def get_active_model(data: dict[str, Any]) -> ModelEntry | None:
    active_id = data.get("app", {}).get("active_model_id", "")
    if not active_id:
        return None
    return find_model(data, active_id)


def repair_registry(data: dict[str, Any]) -> dict[str, Any]:
    """
    Fix broken entries and auto-detect models on disk.
    """
    changed = False

    # Normalize and dedupe by id and path.
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    cleaned: list[dict[str, Any]] = []

    for item in data.get("models", []):
        if not isinstance(item, dict):
            continue

        normalized = _normalize_model(item)
        model_id = normalized["id"]
        model_path = normalized["local_path"]

        if not model_id or model_id in seen_ids:
            changed = True
            continue

        if model_path and model_path in seen_paths:
            changed = True
            continue

        seen_ids.add(model_id)
        if model_path:
            seen_paths.add(model_path)

        cleaned.append(normalized)

    if cleaned != data.get("models", []):
        data["models"] = cleaned
        changed = True

    # Detect models already on disk.
    models_dir = Path.home() / ".local-llm" / "models"
    if models_dir.exists():
        current_ids = {m["id"] for m in data.get("models", [])}
        current_paths = {m["local_path"] for m in data.get("models", [])}

        for folder in models_dir.iterdir():
            if not folder.is_dir():
                continue

            ggufs = list(folder.glob("*.gguf"))
            if not ggufs:
                continue

            model_file = ggufs[0]
            model_path = str(model_file)

            if folder.name in current_ids or model_path in current_paths:
                continue

            new_entry = {
                "id": folder.name,
                "name": model_file.stem,
                "local_path": model_path,
                "source_type": "local",
                "source": model_path,
                "added_at": _utc_now(),
                "alias": model_file.stem,
            }

            data.setdefault("models", []).append(new_entry)
            current_ids.add(folder.name)
            current_paths.add(model_path)
            changed = True

    # Auto-set active model if missing or invalid.
    active_id = data.get("app", {}).get("active_model_id", "")
    if not active_id or find_model(data, active_id) is None:
        if data.get("models"):
            data.setdefault("app", {})["active_model_id"] = data["models"][0]["id"]
            changed = True

    if changed:
        save_registry(data)

    return data