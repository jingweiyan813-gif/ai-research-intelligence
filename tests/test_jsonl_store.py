from __future__ import annotations

import pytest

from airi.storage import JSONLStore


def test_jsonl_write_read_append_iterate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = JSONLStore(tmp_path)

    store.write_jsonl("items.jsonl", [{"id": "1"}, {"id": "2"}])
    store.append_jsonl("items.jsonl", [{"id": "3"}])

    assert store.read_jsonl("items.jsonl") == [
        {"id": "1"},
        {"id": "2"},
        {"id": "3"},
    ]
    assert list(store.iter_jsonl("items.jsonl"))[-1] == {"id": "3"}


def test_jsonl_missing_returns_empty_list(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = JSONLStore(tmp_path)

    assert store.read_jsonl("missing.jsonl") == []


def test_invalid_jsonl_line_reports_line_number(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "items.jsonl").write_text(
        '{"id": "1"}\n\n{broken}\n',
        encoding="utf-8",
    )
    store = JSONLStore(tmp_path)

    with pytest.raises(ValueError, match="line 3"):
        store.read_jsonl("items.jsonl")
