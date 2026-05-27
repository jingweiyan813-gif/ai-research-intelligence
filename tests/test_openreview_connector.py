from __future__ import annotations

from datetime import datetime, timezone

from airi.connectors import OpenReviewConnector
from airi.models import ItemType, SourceType


def openreview_config(**overrides):  # type: ignore[no-untyped-def]
    config = {
        "venues": ["ICLR.cc/2025/Conference"],
        "queries": ["agent"],
        "max_results": 10,
        "freshness_days": None,
        "enabled": True,
    }
    config.update(overrides)
    return config


def note(**overrides):  # type: ignore[no-untyped-def]
    value = {
        "id": "note123",
        "forum": "forum123",
        "invitations": ["ICLR.cc/2025/Conference/-/Submission"],
        "cdate": 1767225600000,
        "mdate": 1767312000000,
        "content": {
            "title": {"value": "Agent Paper"},
            "abstract": {"value": "A paper about agents."},
            "authors": {"value": ["Alice", "Bob"]},
            "keywords": {"value": ["agents", "tool use"]},
            "venue": {"value": "ICLR 2025"},
        },
    }
    value.update(overrides)
    return value


def test_handles_standard_note_fields() -> None:
    connector = OpenReviewConnector(openreview_config())
    raw = connector._note_to_raw(note(), fetched_at=datetime.now(timezone.utc))

    assert raw is not None
    assert raw.source == SourceType.OPENREVIEW
    assert raw.source_item_id == "note123"
    assert raw.raw_title == "Agent Paper"
    assert raw.raw_payload["authors"] == ["Alice", "Bob"]


def test_handles_missing_abstract_authors_gracefully() -> None:
    connector = OpenReviewConnector(openreview_config())
    raw = connector._note_to_raw(
        note(content={"title": "Minimal Paper"}),
        fetched_at=datetime.now(timezone.utc),
    )

    assert raw is not None
    item = connector.normalize(raw)
    assert item.abstract == ""
    assert item.authors == []


def test_maps_venue_keywords_to_paper_signals() -> None:
    connector = OpenReviewConnector(openreview_config())
    raw = connector._note_to_raw(
        note(),
        fetched_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )
    assert raw is not None

    item = connector.normalize(raw)

    assert item.item_type == ItemType.PAPER
    assert item.signals.paper is not None
    assert item.signals.paper.venue == "ICLR 2025"
    assert item.signals.paper.paper_categories == ["agents", "tool use"]
    assert item.keywords == ["agents", "tool use"]


def test_applies_freshness_filter(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = OpenReviewConnector(openreview_config())
    monkeypatch.setattr(connector, "_fetch_json", lambda _: {"notes": [note(cdate=1)]})

    raw_items = connector.fetch_raw(
        since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        limit=2,
    )

    assert raw_items == []


def test_malformed_note_is_skipped() -> None:
    connector = OpenReviewConnector(openreview_config())

    assert connector._note_to_raw({}, fetched_at=datetime.now(timezone.utc)) is None


def test_build_query_urls_include_venue_and_query_limit() -> None:
    connector = OpenReviewConnector(openreview_config())

    urls = connector.build_query_urls(limit=2)

    assert any("invitation=ICLR.cc%2F2025%2FConference" in url for url in urls)
    assert any("term=agent" in url for url in urls)
    assert all("limit=2" in url for url in urls)
