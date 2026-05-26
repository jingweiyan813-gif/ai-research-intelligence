from __future__ import annotations

from datetime import datetime, timezone

from airi.connectors import CompanyBlogsConnector
from airi.models import ItemType, SourceType

RSS_FEED = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Agent launch</title>
      <link>https://example.com/agent?utm_source=rss</link>
      <description>Official agent update.</description>
      <pubDate>Tue, 02 Jan 2026 00:00:00 GMT</pubDate>
      <category>agents</category>
    </item>
  </channel>
</rss>
"""


def company_config(**overrides):  # type: ignore[no-untyped-def]
    config = {
        "feeds": [{"name": "Example AI", "url": "https://example.com/rss.xml"}],
        "keywords": ["agent", "model"],
        "freshness_days": None,
        "max_results": 10,
        "enabled": True,
    }
    config.update(overrides)
    return config


def test_company_connector_parses_feed_and_applies_keyword(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = CompanyBlogsConnector(company_config())
    monkeypatch.setattr(connector, "_fetch_feed_text", lambda _: RSS_FEED)

    raw_items = connector.fetch_raw(limit=2)

    assert len(raw_items) == 1
    assert raw_items[0].source == SourceType.COMPANY_BLOGS
    assert raw_items[0].raw_payload["matched_keywords"] == ["agent"]


def test_company_connector_applies_freshness_filter(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = CompanyBlogsConnector(company_config())
    monkeypatch.setattr(connector, "_fetch_feed_text", lambda _: RSS_FEED)

    raw_items = connector.fetch_raw(
        since=datetime(2027, 1, 1, tzinfo=timezone.utc),
        limit=2,
    )

    assert raw_items == []


def test_company_connector_bad_feed_is_captured(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = CompanyBlogsConnector(company_config())
    monkeypatch.setattr(connector, "_fetch_feed_text", lambda _: "not xml")

    items, result = connector.fetch_and_normalize(limit=2)

    assert items == []
    assert result.raw_count == 0
    assert len(result.errors) == 1
    assert "feed Example AI failed" in result.errors[0]


def test_company_connector_normalize_maps_company_signals(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = CompanyBlogsConnector(company_config())
    monkeypatch.setattr(connector, "_fetch_feed_text", lambda _: RSS_FEED)
    raw = connector.fetch_raw(limit=1)[0]

    item = connector.normalize(raw)

    assert item.source == SourceType.COMPANY_BLOGS
    assert item.item_type == ItemType.COMPANY_UPDATE
    assert item.title == "Agent launch"
    assert item.url == "https://example.com/agent"
    assert item.organizations == ["Example AI"]
    assert item.keywords == ["agents", "agent"]
    assert item.signals.company is not None
    assert item.signals.company.company_name == "Example AI"
    assert item.signals.company.is_official_announcement is True
    assert item.source_payload_hash
    assert item.content_fingerprint


def test_company_connector_keyword_filter_excludes_unmatched(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = CompanyBlogsConnector(company_config(keywords=["quantum"]))
    monkeypatch.setattr(connector, "_fetch_feed_text", lambda _: RSS_FEED)

    assert connector.fetch_raw(limit=2) == []
