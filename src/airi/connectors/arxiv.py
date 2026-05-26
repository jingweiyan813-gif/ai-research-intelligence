from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

from airi.connectors.base import BaseConnector
from airi.models import (
    CommonSignals,
    IntelligenceItem,
    ItemType,
    PaperSignals,
    RawSourceItem,
    SignalBundle,
    SourceMetadata,
    SourceType,
    build_item_id,
)
from airi.normalize import (
    canonicalize_arxiv_url,
    content_fingerprint,
    normalize_text,
    source_payload_hash,
)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
USER_AGENT = "ai-research-intelligence/0.1 (+https://github.com/)"


class ArxivConnector(BaseConnector):
    name = "arxiv"
    source = SourceType.ARXIV
    connector_version = "v1"

    def __init__(self, config: Any) -> None:
        self.config = config
        self.queries = list(_get_config_value(config, "queries", []))
        self.categories = list(_get_config_value(config, "categories", []))
        self.max_results = int(_get_config_value(config, "max_results", 10))
        self.freshness_days = _get_config_value(config, "freshness_days", None)
        self.enabled = bool(_get_config_value(config, "enabled", True))

    def fetch_raw(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[RawSourceItem]:
        if not self.enabled:
            return []
        effective_limit = limit if limit is not None else self.max_results
        cutoff = self._cutoff_datetime(since)
        fetched_at = datetime.now(timezone.utc)
        raw_items: list[RawSourceItem] = []
        seen_ids: set[str] = set()
        query_urls = self.build_query_urls(limit=effective_limit)

        for query_index, url in enumerate(query_urls):
            feed_text = self._fetch_feed_text(url)
            for entry in self._parse_feed(feed_text, fetched_at=fetched_at):
                published_at = _parse_datetime(entry.raw_payload.get("published"))
                updated_at = _parse_datetime(entry.raw_payload.get("updated"))
                newest_at = updated_at or published_at
                if cutoff is not None and newest_at is not None and newest_at < cutoff:
                    continue
                stable_key = entry.source_item_id or entry.raw_url
                if stable_key in seen_ids:
                    continue
                seen_ids.add(stable_key)
                raw_items.append(entry)
                if len(raw_items) >= effective_limit:
                    return raw_items
            if query_index < len(query_urls) - 1:
                time.sleep(0.5)
        return raw_items

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        payload_hash = source_payload_hash(raw.raw_payload)
        title = normalize_text(raw.raw_title)
        summary = normalize_text(raw.raw_text or "")
        canonical_url = canonicalize_arxiv_url(raw.raw_url)
        arxiv_id = raw.source_item_id or canonical_url
        categories = _string_list(raw.raw_payload.get("categories"))
        published_at = _parse_datetime(raw.raw_payload.get("published"))
        authors = _string_list(raw.raw_payload.get("authors"))
        fetched_at = raw.fetched_at
        freshness_days = None
        if published_at is not None:
            freshness_days = max(
                0.0,
                (fetched_at - published_at).total_seconds() / 86400,
            )

        return IntelligenceItem(
            id=build_item_id(SourceType.ARXIV, arxiv_id),
            source=SourceType.ARXIV,
            item_type=ItemType.PAPER,
            title=title,
            url=canonical_url,
            canonical_url=canonical_url,
            abstract=summary,
            authors=authors,
            published_at=published_at,
            fetched_at=fetched_at,
            topics=[],
            entities=[],
            keywords=categories,
            source_metadata=SourceMetadata(
                source=SourceType.ARXIV,
                source_item_id=raw.source_item_id,
                source_url=canonical_url,
                fetched_at=fetched_at,
                connector_name=self.name,
                connector_version=self.connector_version,
                raw_payload_hash=payload_hash,
            ),
            signals=SignalBundle(
                common=CommonSignals(
                    freshness_days=freshness_days,
                    source_importance=0.8,
                ),
                paper=PaperSignals(paper_categories=categories),
            ),
            source_payload_hash=payload_hash,
            content_fingerprint=content_fingerprint(title, summary),
        )

    def build_query_urls(self, *, limit: int | None = None) -> list[str]:
        effective_limit = limit if limit is not None else self.max_results
        search_queries = [f'all:"{query}"' for query in self.queries]
        search_queries.extend(f"cat:{category}" for category in self.categories)
        if not search_queries:
            search_queries = ["cat:cs.AI"]
        return [
            self._build_query_url(query, effective_limit)
            for query in search_queries
        ]

    def _build_query_url(self, search_query: str, max_results: int) -> str:
        params = {
            "search_query": search_query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        return f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"

    def _fetch_feed_text(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            data: bytes = response.read()
            return data.decode("utf-8")

    def _parse_feed(
        self,
        feed_text: str,
        *,
        fetched_at: datetime,
    ) -> list[RawSourceItem]:
        root = ET.fromstring(feed_text)
        raw_items: list[RawSourceItem] = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            raw_item = self._parse_entry(entry, fetched_at=fetched_at)
            if raw_item is not None:
                raw_items.append(raw_item)
        return raw_items

    def _parse_entry(
        self,
        entry: ET.Element,
        *,
        fetched_at: datetime,
    ) -> RawSourceItem | None:
        entry_id = _text(entry, f"{ATOM_NS}id")
        title = normalize_text(_text(entry, f"{ATOM_NS}title"))
        summary = normalize_text(_text(entry, f"{ATOM_NS}summary"))
        if not entry_id or not title:
            return None
        canonical_url = canonicalize_arxiv_url(entry_id)
        arxiv_id = canonical_url.rsplit("/", maxsplit=1)[-1]
        authors = [
            normalize_text(_text(author, f"{ATOM_NS}name"))
            for author in entry.findall(f"{ATOM_NS}author")
        ]
        authors = [author for author in authors if author]
        categories = [
            category.attrib.get("term", "")
            for category in entry.findall(f"{ATOM_NS}category")
        ]
        categories = [category for category in categories if category]
        primary_category = entry.find(f"{ARXIV_NS}primary_category")
        links = [dict(link.attrib) for link in entry.findall(f"{ATOM_NS}link")]
        payload: dict[str, Any] = {
            "id": arxiv_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "published": _text(entry, f"{ATOM_NS}published"),
            "updated": _text(entry, f"{ATOM_NS}updated"),
            "links": links,
            "primary_category": primary_category.attrib.get("term")
            if primary_category is not None
            else None,
        }
        return RawSourceItem(
            source=SourceType.ARXIV,
            source_item_id=arxiv_id,
            raw_url=canonical_url,
            raw_title=title,
            raw_text=summary,
            raw_payload=payload,
            fetched_at=fetched_at,
        )

    def _cutoff_datetime(self, since: datetime | None) -> datetime | None:
        if since is not None:
            return _ensure_timezone(since)
        if self.freshness_days is None:
            return None
        return datetime.now(timezone.utc) - timedelta(days=int(self.freshness_days))


def _get_config_value(config: Any, name: str, default: Any) -> Any:
    if isinstance(config, dict):
        return config.get(name, default)
    return getattr(config, name, default)


def _text(element: ET.Element, path: str) -> str:
    found = element.find(path)
    if found is None or found.text is None:
        return ""
    return found.text


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return _ensure_timezone(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
