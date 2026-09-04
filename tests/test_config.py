import json
from pathlib import Path

from tieny.core.config import ConfigStore, TienyConfig


def test_default_config_values(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")

    config = store.load()

    assert config.preload.model is None
    assert config.preload.auto is False
    assert config.ui.auto_open is True


def test_config_round_trip_preserves_nested_settings(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")

    config = TienyConfig()
    config.preload.model = "abc12345"
    config.preload.auto = True
    config.ui.auto_open = False

    store.save(config)
    loaded = store.load()

    assert loaded.preload.model == "abc12345"
    assert loaded.preload.auto is True
    assert loaded.ui.auto_open is False


def test_old_v020_config_remains_compatible(tmp_path: Path) -> None:
    path = tmp_path / "config.json"

    # Simulate a config written before preload/UI settings existed.
    path.write_text(
        json.dumps(
            {
                "host": "127.0.0.1",
                "port": 8765,
                "log_level": "DEBUG",
                "n_ctx": 2048,
                "n_gpu_layers": 0,
            }
        ),
        encoding="utf-8",
    )

    config = ConfigStore(path).load()

    assert config.host == "127.0.0.1"
    assert config.port == 8765
    assert config.preload.model is None
    assert config.preload.auto is False
    assert config.ui.auto_open is True


def test_invalid_nested_config_types_fall_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"

    path.write_text(
        json.dumps(
            {
                "preload": "invalid",
                "ui": 123,
            }
        ),
        encoding="utf-8",
    )

    config = ConfigStore(path).load()

    assert config.preload.model is None
    assert config.preload.auto is False
    assert config.ui.auto_open is True