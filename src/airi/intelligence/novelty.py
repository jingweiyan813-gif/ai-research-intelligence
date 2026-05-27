from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from airi.models import IntelligenceItem
from airi.storage import StateStore


class NoveltyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    novelty_score: float = Field(ge=0.0, le=1.0)
    reason: str
    seen_before: bool


class NoveltyTracker:
    def __init__(self, state_store: StateStore) -> None:
        self.state_store = state_store

    def compute(self, items: list[IntelligenceItem]) -> dict[str, NoveltyResult]:
        seen = self.state_store.load_seen_items()
        id_index = self._index_seen(seen, "item_id")
        url_index = self._index_seen(seen, "canonical_url")
        fingerprint_index = self._index_seen(seen, "content_fingerprint")
        results = {}
        for item in items:
            canonical_url = item.canonical_url or item.url
            if item.id in id_index:
                results[item.id] = NoveltyResult(
                    item_id=item.id,
                    novelty_score=0.0,
                    reason="item id seen before",
                    seen_before=True,
                )
            elif canonical_url in url_index:
                results[item.id] = NoveltyResult(
                    item_id=item.id,
                    novelty_score=0.0,
                    reason="canonical url seen before",
                    seen_before=True,
                )
            elif item.content_fingerprint in fingerprint_index:
                results[item.id] = NoveltyResult(
                    item_id=item.id,
                    novelty_score=0.1,
                    reason="content fingerprint seen before",
                    seen_before=True,
                )
            else:
                results[item.id] = NoveltyResult(
                    item_id=item.id,
                    novelty_score=1.0,
                    reason="new item",
                    seen_before=False,
                )
        return results

    def update_seen(self, items: list[IntelligenceItem]) -> None:
        seen = self.state_store.load_seen_items()
        now = datetime.now(timezone.utc).isoformat()
        for item in items:
            key = item.id
            existing = seen.get(key)
            if not isinstance(existing, dict):
                existing = {}
            first_seen_at = existing.get("first_seen_at") or now
            seen[key] = {
                "item_id": item.id,
                "canonical_url": item.canonical_url or item.url,
                "content_fingerprint": item.content_fingerprint,
                "title": item.title,
                "source": item.source.value,
                "first_seen_at": first_seen_at,
                "last_seen_at": now,
                "seen_count": int(existing.get("seen_count", 0)) + 1,
            }
        self.state_store.save_seen_items(seen)

    def _index_seen(self, seen: dict[str, Any], field: str) -> set[str]:
        values = set()
        for record in seen.values():
            if not isinstance(record, dict):
                continue
            value = record.get(field)
            if isinstance(value, str) and value:
                values.add(value)
        return values
