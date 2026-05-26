from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from airi.models import RawSourceItem, SourceType


def test_raw_source_item_valid() -> None:
    item = RawSourceItem(
        source=SourceType.HACKERNEWS,
        raw_url="https://news.ycombinator.com/item?id=1",
        raw_title="A discussion",
        raw_payload={"id": 1},
        fetched_at=datetime.now(timezone.utc),
    )

    assert item.raw_payload["id"] == 1


def test_raw_source_item_empty_title_fails() -> None:
    with pytest.raises(ValidationError):
        RawSourceItem(
            source=SourceType.HACKERNEWS,
            raw_url="https://news.ycombinator.com/item?id=1",
            raw_title="",
            fetched_at=datetime.now(timezone.utc),
        )
