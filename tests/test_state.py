from pathlib import Path

from tieny.core.state import StateStore


def test_default_state_has_no_last_used_model(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")

    state = store.load()

    assert state.last_used_model is None


def test_last_used_model_persists(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")

    store.set_last_used_model("tiny-id")

    state = store.load()

    assert state.last_used_model == "tiny-id"


def test_last_used_model_can_be_replaced(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")

    store.set_last_used_model("tiny-id")
    store.set_last_used_model("small-id")

    state = store.load()

    assert state.last_used_model == "small-id"


def test_invalid_state_json_falls_back_safely(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{this is broken json", encoding="utf-8")

    state = StateStore(path).load()

    assert state.last_used_model is None