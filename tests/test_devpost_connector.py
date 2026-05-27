from __future__ import annotations

from datetime import datetime, timezone

from airi.connectors import DevpostConnector
from airi.models import ItemType, SourceType

HTML = """
<html><body>
<article class="hackathon-tile">
  <h3>AI Agent Hackathon</h3>
  <a href="https://devpost.com/software/ai-agent-hackathon">View</a>
  <p>Build developer tools with LLM agents. Deadline: Mar 10, 2026.</p>
  <span class="tag">AI</span><span class="tag">Developer Tools</span>
  <span>$10,000 in prizes</span><span>Remote</span>
</article>
<article class="hackathon-tile">
  <h3>Unrelated Cooking Event</h3>
  <a href="https://devpost.com/software/cooking-event">View</a>
  <p>Food only. Deadline: Mar 10, 2026.</p>
</article>
</body></html>
"""


def devpost_config(**overrides):  # type: ignore[no-untyped-def]
    config = {
        "keywords": ["ai agent", "developer tools"],
        "max_results": 10,
        "days_ahead": None,
        "enabled": True,
        "listing_urls": ["https://devpost.com/hackathons"],
    }
    config.update(overrides)
    return config


def test_parses_mocked_listing_html(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = DevpostConnector(devpost_config())
    monkeypatch.setattr(connector, "_fetch_text", lambda _: HTML)

    raw_items = connector.fetch_raw(limit=2)

    assert len(raw_items) == 1
    assert raw_items[0].source == SourceType.DEVPOST
    assert raw_items[0].raw_title == "AI Agent Hackathon"
    assert raw_items[0].raw_payload["prize"] == "$10,000 in prizes"
    assert raw_items[0].raw_payload["is_remote"] is True


def test_normalize_maps_hackathon_signals(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = DevpostConnector(devpost_config())
    monkeypatch.setattr(connector, "_fetch_text", lambda _: HTML)
    raw = connector.fetch_raw(limit=1)[0]

    item = connector.normalize(raw)

    assert item.source == SourceType.DEVPOST
    assert item.item_type == ItemType.HACKATHON
    assert item.title == "AI Agent Hackathon"
    assert item.url == "https://devpost.com/software/ai-agent-hackathon"
    assert item.signals.hackathon is not None
    assert item.signals.hackathon.prize_amount == "$10,000 in prizes"
    assert item.signals.hackathon.is_remote is True
    assert item.keywords == ["AI", "Developer Tools", "ai agent", "developer tools"]


def test_applies_keyword_filter(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = DevpostConnector(devpost_config(keywords=["quantum"]))
    monkeypatch.setattr(connector, "_fetch_text", lambda _: HTML)

    assert connector.fetch_raw(limit=2) == []


def test_applies_days_ahead_filter(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = DevpostConnector(devpost_config())
    monkeypatch.setattr(connector, "_fetch_text", lambda _: HTML)

    raw_items = connector.fetch_raw(
        since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        limit=2,
    )

    assert raw_items == []


def test_malformed_card_is_skipped() -> None:
    connector = DevpostConnector(devpost_config())

    assert (
        connector.parse_listing("<article>missing title</article>", listing_url="x")
        == []
    )
