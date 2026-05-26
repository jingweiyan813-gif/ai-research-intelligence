from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from airi.connectors.base import BaseConnector
from airi.models import (
    IntelligenceItem,
    ItemType,
    RawSourceItem,
    SignalBundle,
    SourceMetadata,
    SourceType,
    build_item_id,
)
from airi.normalize import content_fingerprint, source_payload_hash


class FakeConnector(BaseConnector):
    name = "fake"
    source = SourceType.UNKNOWN
    connector_version = "v1"

    def __init__(
        self,
        *,
        item_count: int = 3,
        fail_fetch: bool = False,
        fail_normalize_index: int | None = None,
    ) -> None:
        if item_count < 0:
            raise ValueError("item_count must be non-negative")
        self.item_count = item_count
        self.fail_fetch = fail_fetch
        self.fail_normalize_index = fail_normalize_index
        self._base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def fetch_raw(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[RawSourceItem]:
        if self.fail_fetch:
            raise RuntimeError("fake fetch failure")
        count = self.item_count if limit is None else min(self.item_count, limit)
        return [self._raw_item(index) for index in range(count)]

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        index = int(raw.source_item_id or "0")
        if self.fail_normalize_index == index:
            raise ValueError(f"fake normalize failure at index {index}")
        payload_hash = source_payload_hash(raw.raw_payload)
        fingerprint = content_fingerprint(raw.raw_title, raw.raw_text)
        item_id = build_item_id(self.source, raw.source_item_id or raw.raw_url)
        return IntelligenceItem(
            id=item_id,
            source=self.source,
            item_type=ItemType.UNKNOWN,
            title=raw.raw_title,
            url=raw.raw_url,
            content_snippet=raw.raw_text,
            fetched_at=raw.fetched_at,
            topics=["fake_topic"],
            keywords=["fake", "smoke"],
            source_metadata=SourceMetadata(
                source=self.source,
                source_item_id=raw.source_item_id,
                source_url=raw.raw_url,
                fetched_at=raw.fetched_at,
                connector_name=self.name,
                connector_version=self.connector_version,
                raw_payload_hash=payload_hash,
            ),
            signals=SignalBundle(),
            source_payload_hash=payload_hash,
            content_fingerprint=fingerprint,
        )

    def _raw_item(self, index: int) -> RawSourceItem:
        payload: dict[str, Any] = {
            "id": f"fake-{index}",
            "title": f"Fake Intelligence Item {index}",
            "url": f"https://example.com/fake/{index}",
        }
        return RawSourceItem(
            source=self.source,
            source_item_id=str(index),
            raw_url=payload["url"],
            raw_title=payload["title"],
            raw_text=f"Deterministic fake body {index}.",
            raw_payload=payload,
            fetched_at=self._base_time + timedelta(minutes=index),
        )
