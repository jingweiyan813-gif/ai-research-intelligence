from __future__ import annotations

import json

import pytest

from airi.storage import JSONStore


def test_json_read_write(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = JSONStore(tmp_path)

    path = store.write_json("nested/state.json", {"hello": "世界"})

    assert path.exists()
    assert store.read_json("nested/state.json") == {"hello": "世界"}


def test_json_missing_returns_default(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = JSONStore(tmp_path)

    assert store.read_json("missing.json", default={"empty": True}) == {"empty": True}


def test_invalid_json_raises_value_error(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    store = JSONStore(tmp_path)

    with pytest.raises(ValueError, match="Invalid JSON file"):
        store.read_json("broken.json")


def test_json_atomic_write_produces_valid_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = JSONStore(tmp_path)

    store.write_json("state.json", {"value": 1})
    store.write_json("state.json", {"value": 2})

    with (tmp_path / "state.json").open("r", encoding="utf-8") as file:
        assert json.load(file) == {"value": 2}


def test_json_delete_and_exists(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = JSONStore(tmp_path)
    store.write_json("state.json", {"value": 1})

    assert store.exists("state.json")
    assert store.delete("state.json") is True
    assert store.delete("state.json") is False
