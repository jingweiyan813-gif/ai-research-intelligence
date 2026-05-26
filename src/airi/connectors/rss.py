from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from airi.connectors.base import BaseConnector
from airi.models import IntelligenceItem, RawSourceItem, SourceType
from airi.normalize import canonicalize_url, normalize_text

ATOM_NS = "{http://www.w3.org/2005/Atom}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
USER_AGENT = "ai-research-intelligence"


class RSSConnector(BaseConnector):
    name = "rss"
    source = SourceType.RSS
    connector_version = "v1"

    def __init__(self, feeds: list[dict[str, str]] | None = None) -> None:
        self.feeds = feeds or []

    def fetch_raw(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[RawSourceItem]:
        fetched_at = datetime.now(timezone.utc)
        raw_items: list[RawSourceItem] = []
        for feed in self.feeds:
            feed_name = feed.get("name") or "RSS Feed"
            feed_url = feed.get("url")
            if not feed_url:
                continue
            feed_text = self._fetch_feed_text(feed_url)
            raw_items.extend(
                self.parse_feed(
                    feed_text,
                    feed_name=feed_name,
                    feed_url=feed_url,
                    fetched_at=fetched_at,
                )
            )
            if limit is not None and len(raw_items) >= limit:
                return raw_items[:limit]
        return raw_items

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        raise NotImplementedError("Use a concrete RSS connector for normalization")

    def _fetch_feed_text(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            data: bytes = response.read()
        return data.decode("utf-8")

    def parse_feed(
        self,
        feed_text: str,
        *,
        feed_name: str,
        feed_url: str,
        fetched_at: datetime,
    ) -> list[RawSourceItem]:
        root = ET.fromstring(feed_text)
        if root.tag == f"{ATOM_NS}feed":
            return self._parse_atom(root, feed_name=feed_name, fetched_at=fetched_at)
        return self._parse_rss(root, feed_name=feed_name, fetched_at=fetched_at)

    def _parse_atom(
        self,
        root: ET.Element,
        *,
        feed_name: str,
        fetched_at: datetime,
    ) -> list[RawSourceItem]:
        items = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            title = normalize_text(_text(entry, f"{ATOM_NS}title"))
            link = _atom_link(entry)
            if not title or not link:
                continue
            summary = normalize_text(
                _text(entry, f"{ATOM_NS}summary") or _text(entry, f"{ATOM_NS}content")
            )
            tags = [
                category.attrib.get("term", "")
                for category in entry.findall(f"{ATOM_NS}category")
            ]
            payload = {
                "feed_name": feed_name,
                "title": title,
                "link": link,
                "summary": summary,
                "published": _text(entry, f"{ATOM_NS}published"),
                "updated": _text(entry, f"{ATOM_NS}updated"),
                "tags": [tag for tag in tags if tag],
            }
            items.append(_raw_from_payload(payload, fetched_at=fetched_at))
        return items

    def _parse_rss(
        self,
        root: ET.Element,
        *,
        feed_name: str,
        fetched_at: datetime,
    ) -> list[RawSourceItem]:
        items = []
        for entry in root.findall(".//item"):
            title = normalize_text(_text(entry, "title"))
            link = _text(entry, "link")
            if not title or not link:
                continue
            summary = normalize_text(
                _text(entry, "description") or _text(entry, f"{CONTENT_NS}encoded")
            )
            tags = [_text(category, ".") for category in entry.findall("category")]
            payload = {
                "feed_name": feed_name,
                "title": title,
                "link": link,
                "summary": summary,
                "published": _text(entry, "pubDate"),
                "updated": _text(entry, "updated"),
                "tags": [tag for tag in tags if tag],
            }
            items.append(_raw_from_payload(payload, fetched_at=fetched_at))
        return items


def parse_feed_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _raw_from_payload(
    payload: dict[str, Any],
    *,
    fetched_at: datetime,
) -> RawSourceItem:
    link = str(payload["link"])
    summary = payload.get("summary")
    return RawSourceItem(
        source=SourceType.RSS,
        source_item_id=str(payload.get("id") or link),
        raw_url=canonicalize_url(link),
        raw_title=str(payload["title"]),
        raw_text=summary if isinstance(summary, str) else None,
        raw_payload=payload,
        fetched_at=fetched_at,
    )


def _text(element: ET.Element, path: str) -> str:
    found = element if path == "." else element.find(path)
    if found is None or found.text is None:
        return ""
    return found.text


def _atom_link(entry: ET.Element) -> str:
    for link in entry.findall(f"{ATOM_NS}link"):
        href = link.attrib.get("href")
        rel = link.attrib.get("rel", "alternate")
        if href and rel == "alternate":
            return href
    first_link = entry.find(f"{ATOM_NS}link")
    if first_link is None:
        return ""
    return first_link.attrib.get("href", "")
