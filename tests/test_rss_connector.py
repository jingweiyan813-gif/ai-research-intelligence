from __future__ import annotations

from datetime import datetime, timezone

from airi.connectors import RSSConnector

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

ATOM_FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Model update</title>
    <link href="https://example.com/model" rel="alternate" />
    <summary>Official model update.</summary>
    <updated>2026-01-03T00:00:00Z</updated>
    <category term="models" />
  </entry>
</feed>
"""


def test_rss_connector_parses_rss_feed_entries() -> None:
    connector = RSSConnector()

    items = connector.parse_feed(
        RSS_FEED,
        feed_name="Example Feed",
        feed_url="https://example.com/rss.xml",
        fetched_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    assert len(items) == 1
    assert items[0].raw_title == "Agent launch"
    assert items[0].raw_url == "https://example.com/agent"
    assert items[0].raw_payload["tags"] == ["agents"]


def test_rss_connector_parses_atom_feed_entries() -> None:
    connector = RSSConnector()

    items = connector.parse_feed(
        ATOM_FEED,
        feed_name="Example Feed",
        feed_url="https://example.com/atom.xml",
        fetched_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    assert len(items) == 1
    assert items[0].raw_title == "Model update"
    assert items[0].raw_payload["tags"] == ["models"]
