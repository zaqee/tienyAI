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
    source_type: str  # "path" or "url"
    source: str
    local_path: str
    added_at: str

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


def _load_toml(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        with path.open("rb") as f:
            data = parse(f.read().decode("utf-8"))
        return _tomlkit_to_plain(data, fallback)
    except Exception:
        # A broken config should never prevent the server from starting.
        return fallback


def _tomlkit_to_plain(value: Any, fallback: Any) -> Any:
    if isinstance(value, dict):
        return {k: _tomlkit_to_plain(v, fallback.get(k) if isinstance(fallback, dict) else None) for k, v in value.items()}
    if isinstance(value, list):
        return [_tomlkit_to_plain(item, fallback[0] if isinstance(fallback, list) and fallback else None) for item in value]
    return value


def load_registry() -> dict[str, Any]:
    ensure_app_dirs()
    data = _load_toml(REGISTRY_PATH, default_registry())
    data.setdefault("app", {}).setdefault("active_model_id", "")
    data.setdefault("settings", {})
    data.setdefault("models", [])
    # Merge missing defaults so the rest of the code can assume keys exist.
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
        for field in ("id", "name", "source_type", "source", "local_path", "added_at"):
            model_table.add(field, item.get(field, ""))
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
    return [ModelEntry(**item) for item in data.get("models", [])]


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



def repair_registry(data: dict) -> dict:
    """
    Fix broken entries + auto-detect models on disk.
    """
    changed = False

    # Fix existing entries
    for item in data.get("models", []):
        if "local_path" not in item and "path" in item:
            item["local_path"] = item.pop("path")
            changed = True

        item.setdefault("source_type", "local")
        item.setdefault("source", item.get("local_path", ""))
        item.setdefault("added_at", datetime.utcnow().isoformat())

    # Detect models on disk
    models_dir = Path.home() / ".local-llm" / "models"

    if models_dir.exists():
        known_ids = {m["id"] for m in data.get("models", [])}

        for folder in models_dir.iterdir():
            if not folder.is_dir():
                continue

            if folder.name in known_ids:
                continue

            ggufs = list(folder.glob("*.gguf"))
            if not ggufs:
                continue

            model_file = ggufs[0]

            new_entry = {
                "id": folder.name,
                "name": model_file.stem,
                "local_path": str(model_file),
                "source_type": "local",
                "source": str(model_file),
                "added_at": datetime.utcnow().isoformat(),
            }

            data.setdefault("models", []).append(new_entry)
            changed = True

    # Auto-set active model
    if not data.get("app", {}).get("active_model_id") and data.get("models"):
        data.setdefault("app", {})
        data["app"]["active_model_id"] = data["models"][0]["id"]
        changed = True

    if changed:
        from .registry import save_registry
        save_registry(data)

    return data