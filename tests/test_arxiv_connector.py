from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

from airi.connectors import ArxivConnector
from airi.models import ItemType, SourceType

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>https://arxiv.org/pdf/2401.12345v2</id>
    <updated>2026-01-03T00:00:00Z</updated>
    <published>2026-01-02T00:00:00Z</published>
    <title>  A Paper About AI Agents  </title>
    <summary>  This paper studies agent systems.  </summary>
    <author><name>Alice Example</name></author>
    <author><name>Bob Example</name></author>
    <arxiv:primary_category term="cs.AI" />
    <category term="cs.AI" />
    <category term="cs.SE" />
    <link href="https://arxiv.org/abs/2401.12345v2" rel="alternate" />
    <link href="https://arxiv.org/pdf/2401.12345v2" rel="related" title="pdf" />
  </entry>
  <entry>
    <id>https://arxiv.org/abs/2401.99999</id>
    <updated>2020-01-03T00:00:00Z</updated>
    <published>2020-01-02T00:00:00Z</published>
    <title>Old Paper</title>
    <summary>Old summary.</summary>
    <author><name>Carol Example</name></author>
    <category term="cs.CL" />
  </entry>
  <entry>
    <id></id>
    <title></title>
    <summary>Malformed.</summary>
  </entry>
</feed>
"""


def arxiv_config(**overrides):  # type: ignore[no-untyped-def]
    config = {
        "queries": ["AI agent", "coding agent"],
        "categories": ["cs.AI", "cs.SE"],
        "max_results": 10,
        "freshness_days": None,
        "enabled": True,
    }
    config.update(overrides)
    return config


def test_query_url_construction_includes_queries_and_categories() -> None:
    connector = ArxivConnector(arxiv_config())

    urls = connector.build_query_urls(limit=2)
    decoded_queries = [
        urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["search_query"][0]
        for url in urls
    ]

    assert 'all:"AI agent"' in decoded_queries
    assert 'all:"coding agent"' in decoded_queries
    assert "cat:cs.AI" in decoded_queries
    assert "cat:cs.SE" in decoded_queries
    assert all("max_results=2" in url for url in urls)


def test_limit_overrides_config_max_results(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = ArxivConnector(arxiv_config(max_results=10))
    called_urls: list[str] = []

    def fake_fetch(url: str) -> str:
        called_urls.append(url)
        return ATOM_FEED

    monkeypatch.setattr(connector, "_fetch_feed_text", fake_fetch)
    monkeypatch.setattr("airi.connectors.arxiv.time.sleep", lambda _: None)

    raw_items = connector.fetch_raw(limit=1)

    assert len(raw_items) == 1
    assert "max_results=1" in called_urls[0]


def test_atom_response_maps_to_raw_source_item(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = ArxivConnector(arxiv_config(queries=["AI agent"], categories=[]))
    monkeypatch.setattr(connector, "_fetch_feed_text", lambda _: ATOM_FEED)

    raw_items = connector.fetch_raw(
        since=datetime(2025, 1, 1, tzinfo=timezone.utc),
        limit=5,
    )

    assert len(raw_items) == 1
    raw = raw_items[0]
    assert raw.source == SourceType.ARXIV
    assert raw.source_item_id == "2401.12345v2"
    assert raw.raw_url == "https://arxiv.org/abs/2401.12345v2"
    assert raw.raw_title == "A Paper About AI Agents"
    assert raw.raw_payload["authors"] == ["Alice Example", "Bob Example"]
    assert raw.raw_payload["categories"] == ["cs.AI", "cs.SE"]


def test_normalize_maps_metadata_and_canonicalizes_pdf_url() -> None:
    connector = ArxivConnector(arxiv_config())
    raw_items = connector._parse_feed(
        ATOM_FEED,
        fetched_at=datetime(2026, 1, 4, tzinfo=timezone.utc),
    )
    raw = raw_items[0]

    item = connector.normalize(raw)

    assert item.source == SourceType.ARXIV
    assert item.item_type == ItemType.PAPER
    assert item.title == "A Paper About AI Agents"
    assert item.url == "https://arxiv.org/abs/2401.12345v2"
    assert item.canonical_url == "https://arxiv.org/abs/2401.12345v2"
    assert item.abstract == "This paper studies agent systems."
    assert item.authors == ["Alice Example", "Bob Example"]
    assert item.keywords == ["cs.AI", "cs.SE"]
    assert item.published_at == datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert item.signals.paper is not None
    assert item.signals.paper.paper_categories == ["cs.AI", "cs.SE"]
    assert item.source_metadata.connector_name == "arxiv"


def test_freshness_filter_excludes_old_papers(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = ArxivConnector(arxiv_config(queries=["AI agent"], categories=[]))
    monkeypatch.setattr(connector, "_fetch_feed_text", lambda _: ATOM_FEED)

    raw_items = connector.fetch_raw(
        since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        limit=10,
    )

    assert [item.source_item_id for item in raw_items] == ["2401.12345v2"]


def test_malformed_entries_are_skipped_without_crashing() -> None:
    connector = ArxivConnector(arxiv_config())

    raw_items = connector._parse_feed(ATOM_FEED, fetched_at=datetime.now(timezone.utc))

    assert len(raw_items) == 2
