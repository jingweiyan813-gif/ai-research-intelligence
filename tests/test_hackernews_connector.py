from __future__ import annotations

from datetime import datetime, timezone

from airi.connectors import HackerNewsConnector
from airi.models import ItemType, SourceType


def hn_config(**overrides):  # type: ignore[no-untyped-def]
    config = {
        "keywords": ["AI agent", "LLM"],
        "min_score": 10,
        "freshness_days": None,
        "max_results": 10,
        "enabled": True,
    }
    config.update(overrides)
    return config


def hn_item(**overrides):  # type: ignore[no-untyped-def]
    item = {
        "id": 1,
        "type": "story",
        "by": "alice",
        "time": 1767225600,
        "title": "New AI agent framework",
        "url": "https://example.com/agent?utm_source=hn#comments",
        "score": 42,
        "descendants": 8,
        "kids": [2, 3, 4],
    }
    item.update(overrides)
    return item


def test_fetch_ids_then_item_payloads(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = HackerNewsConnector(hn_config())

    monkeypatch.setattr(connector, "_story_ids", lambda: [1])
    monkeypatch.setattr(connector, "_fetch_item", lambda story_id: hn_item(id=story_id))

    raw_items = connector.fetch_raw(limit=1)

    assert len(raw_items) == 1
    assert raw_items[0].source == SourceType.HACKERNEWS
    assert raw_items[0].source_item_id == "1"
    assert raw_items[0].raw_payload["kids_count"] == 3


def test_filters_by_keyword(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = HackerNewsConnector(hn_config(keywords=["AI agent"]))
    monkeypatch.setattr(connector, "_story_ids", lambda: [1, 2])
    monkeypatch.setattr(
        connector,
        "_fetch_item",
        lambda story_id: hn_item(id=story_id, title="Unrelated database news"),
    )

    assert connector.fetch_raw(limit=2) == []


def test_filters_by_min_score(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = HackerNewsConnector(hn_config(min_score=50))
    monkeypatch.setattr(connector, "_story_ids", lambda: [1])
    monkeypatch.setattr(connector, "_fetch_item", lambda _: hn_item(score=20))

    assert connector.fetch_raw(limit=1) == []


def test_filters_stale_items(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = HackerNewsConnector(hn_config())
    monkeypatch.setattr(connector, "_story_ids", lambda: [1])
    monkeypatch.setattr(connector, "_fetch_item", lambda _: hn_item(time=1577836800))

    assert connector.fetch_raw(
        since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        limit=1,
    ) == []


def test_skips_dead_deleted_items(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = HackerNewsConnector(hn_config())
    monkeypatch.setattr(connector, "_story_ids", lambda: [1, 2])
    monkeypatch.setattr(
        connector,
        "_fetch_item",
        lambda story_id: hn_item(id=story_id, dead=True),
    )

    assert connector.fetch_raw(limit=2) == []


def test_normalize_maps_score_comments_and_keywords() -> None:
    connector = HackerNewsConnector(hn_config())
    raw = connector._item_to_raw(
        hn_item(),
        fetched_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        cutoff=None,
    )
    assert raw is not None

    item = connector.normalize(raw)

    assert item.source == SourceType.HACKERNEWS
    assert item.item_type == ItemType.DISCUSSION
    assert item.title == "New AI agent framework"
    assert item.url == "https://example.com/agent"
    assert item.authors == ["alice"]
    assert item.keywords == ["AI agent"]
    assert item.signals.community is not None
    assert item.signals.community.hn_score == 42
    assert item.signals.community.hn_comments == 8


def test_item_without_url_uses_hn_url_if_title_matches() -> None:
    connector = HackerNewsConnector(hn_config(keywords=["AI agent"]))
    raw = connector._item_to_raw(
        hn_item(url=None),
        fetched_at=datetime.now(timezone.utc),
        cutoff=None,
    )

    assert raw is not None
    assert raw.raw_url == "https://news.ycombinator.com/item?id=1"
