from __future__ import annotations

from airi.connectors import FakeConnector
from airi.models import SourceType


def test_fake_connector_returns_deterministic_items() -> None:
    first_connector = FakeConnector(item_count=2)
    second_connector = FakeConnector(item_count=2)

    first_items, first_result = first_connector.fetch_and_normalize()
    second_items, second_result = second_connector.fetch_and_normalize()

    assert [item.id for item in first_items] == [item.id for item in second_items]
    assert [item.title for item in first_items] == [item.title for item in second_items]
    assert first_result.source == SourceType.UNKNOWN
    assert second_result.source == SourceType.UNKNOWN


def test_fake_connector_limit_reduces_raw_items() -> None:
    connector = FakeConnector(item_count=5)

    items, result = connector.fetch_and_normalize(limit=2)

    assert len(items) == 2
    assert result.raw_count == 2
