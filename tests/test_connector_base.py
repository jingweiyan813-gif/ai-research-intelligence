from __future__ import annotations

from airi.connectors import FakeConnector


def test_fetch_and_normalize_counts_raw_and_normalized_items() -> None:
    connector = FakeConnector(item_count=3)

    items, result = connector.fetch_and_normalize()

    assert len(items) == 3
    assert result.raw_count == 3
    assert result.normalized_count == 3
    assert result.errors == []
    assert result.completed_at is not None


def test_item_level_normalization_error_is_captured() -> None:
    connector = FakeConnector(item_count=3, fail_normalize_index=1)

    items, result = connector.fetch_and_normalize()

    assert len(items) == 2
    assert result.raw_count == 3
    assert result.normalized_count == 2
    assert len(result.errors) == 1
    assert "normalize item 1 failed" in result.errors[0]


def test_fetch_raw_failure_is_captured() -> None:
    connector = FakeConnector(fail_fetch=True)

    items, result = connector.fetch_and_normalize()

    assert items == []
    assert result.raw_count == 0
    assert result.normalized_count == 0
    assert len(result.errors) == 1
    assert "fetch_raw failed" in result.errors[0]
