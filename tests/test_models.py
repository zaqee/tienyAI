from pathlib import Path

import pytest

from tieny.models.registry import ModelRegistry
from tieny.models.service import ModelService


def service(tmp_path: Path) -> ModelService:
    return ModelService(ModelRegistry(tmp_path / "models.json"))


def make_gguf(path: Path, name: str = "qwen.gguf") -> Path:
    model = path / name
    model.write_bytes(b"fake-gguf-for-registry-test")
    return model


def test_add_stores_path_without_copying(tmp_path: Path) -> None:
    svc = service(tmp_path)
    original = make_gguf(tmp_path)
    record = svc.add(str(original))
    assert Path(record.path) == original.resolve()
    assert original.exists()
    assert len(list(tmp_path.glob("*.gguf"))) == 1


def test_name_collision_adds_number(tmp_path: Path) -> None:
    svc = service(tmp_path)
    first_dir = tmp_path / "one"
    second_dir = tmp_path / "two"
    first_dir.mkdir(); second_dir.mkdir()
    first = svc.add(str(make_gguf(first_dir, "qwen.gguf")))
    second = svc.add(str(make_gguf(second_dir, "qwen.gguf")))
    assert first.name == "qwen"
    assert second.name == "qwen1"


def test_all_targets_resolve_by_id_or_name(tmp_path: Path) -> None:
    svc = service(tmp_path)
    model = svc.add(str(make_gguf(tmp_path)))
    assert svc.resolve(model.id).id == model.id
    assert svc.resolve(model.name).id == model.id


def test_reset_name_uses_filename_and_collision_rule(tmp_path: Path) -> None:
    svc = service(tmp_path)
    d1, d2 = tmp_path / "a", tmp_path / "b"
    d1.mkdir(); d2.mkdir()
    first = svc.add(str(make_gguf(d1, "qwen.gguf")))
    second = svc.add(str(make_gguf(d2, "other.gguf")))
    svc.rename(second.id, "custom")
    # Put second behind a filename that would collide with first when reset.
    renamed_file = d2 / "qwen.gguf"
    Path(second.path).rename(renamed_file)
    models = svc.list()
    for item in models:
        if item.id == second.id:
            item.path = str(renamed_file.resolve())
    svc.registry.replace_all(models)
    reset = svc.reset_name(second.id)
    assert first.name == "qwen"
    assert reset.name == "qwen1"


def test_remove_default_never_deletes_original(tmp_path: Path) -> None:
    svc = service(tmp_path)
    original = make_gguf(tmp_path)
    record = svc.add(str(original))
    svc.remove(record.id)
    assert original.exists()
    assert svc.list() == []


def test_remove_del_deletes_original(tmp_path: Path) -> None:
    svc = service(tmp_path)
    original = make_gguf(tmp_path)
    record = svc.add(str(original))
    svc.remove(record.name, delete_file=True)
    assert not original.exists()
    assert svc.list() == []
