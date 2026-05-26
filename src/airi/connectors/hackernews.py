from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from airi.connectors.base import BaseConnector
from airi.models import (
    CommonSignals,
    CommunitySignals,
    IntelligenceItem,
    ItemType,
    RawSourceItem,
    SignalBundle,
    SourceMetadata,
    SourceType,
    build_item_id,
)
from airi.normalize import (
    canonicalize_url,
    content_fingerprint,
    normalize_for_matching,
    normalize_text,
    source_payload_hash,
)

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_NEW_STORIES_URL = "https://hacker-news.firebaseio.com/v0/newstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
HN_WEB_ITEM_URL = "https://news.ycombinator.com/item?id={item_id}"
USER_AGENT = "ai-research-intelligence"


class HackerNewsConnector(BaseConnector):
    name = "hackernews"
    source = SourceType.HACKERNEWS
    connector_version = "v1"

    def __init__(self, config: Any) -> None:
        self.config = config
        self.keywords = list(_get_config_value(config, "keywords", []))
        self.min_score = _get_config_value(config, "min_score", None)
        self.freshness_days = _get_config_value(config, "freshness_days", None)
        self.max_results = int(_get_config_value(config, "max_results", 20))
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
        seen_ids: set[int] = set()
        fetched_count = 0

        for story_id in self._story_ids():
            if fetched_count >= effective_limit:
                break
            if story_id in seen_ids:
                continue
            seen_ids.add(story_id)
            fetched_count += 1
            payload = self._fetch_item(story_id)
            if not isinstance(payload, dict):
                continue
            raw_item = self._item_to_raw(payload, fetched_at=fetched_at, cutoff=cutoff)
            if raw_item is None:
                continue
            raw_items.append(raw_item)
            if len(raw_items) >= effective_limit:
                return raw_items
        return raw_items

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        payload_hash = source_payload_hash(raw.raw_payload)
        title = normalize_text(raw.raw_title)
        snippet = normalize_text(raw.raw_text or title)
        canonical = canonicalize_url(raw.raw_url)
        published_at = _hn_time_to_datetime(raw.raw_payload.get("time"))
        author = raw.raw_payload.get("by")
        matched_keywords = self._matched_keywords(
            f"{title} {raw.raw_payload.get('url') or ''}"
        )
        fetched_at = raw.fetched_at
        freshness_days = None
        if published_at is not None:
            freshness_days = max(
                0.0,
                (fetched_at - published_at).total_seconds() / 86400,
            )

        return IntelligenceItem(
            id=build_item_id(SourceType.HACKERNEWS, raw.source_item_id or canonical),
            source=SourceType.HACKERNEWS,
            item_type=ItemType.DISCUSSION,
            title=title,
            url=canonical,
            canonical_url=canonical,
            abstract=snippet,
            content_snippet=snippet,
            authors=[author] if isinstance(author, str) and author else [],
            organizations=[],
            repos=[],
            papers=[],
            published_at=published_at,
            fetched_at=fetched_at,
            topics=[],
            entities=[],
            keywords=matched_keywords,
            source_metadata=SourceMetadata(
                source=SourceType.HACKERNEWS,
                source_item_id=raw.source_item_id,
                source_url=canonical,
                fetched_at=fetched_at,
                connector_name=self.name,
                connector_version=self.connector_version,
                raw_payload_hash=payload_hash,
            ),
            signals=SignalBundle(
                common=CommonSignals(
                    freshness_days=freshness_days,
                    source_importance=0.6,
                ),
                community=CommunitySignals(
                    hn_score=_optional_int(raw.raw_payload.get("score")),
                    hn_comments=_optional_int(raw.raw_payload.get("descendants")),
                ),
            ),
            source_payload_hash=payload_hash,
            content_fingerprint=content_fingerprint(title, snippet),
        )

    def _story_ids(self) -> list[int]:
        ids: list[int] = []
        for url in (HN_TOP_STORIES_URL, HN_NEW_STORIES_URL):
            data = self._fetch_json(url)
            if not isinstance(data, list):
                continue
            ids.extend(item for item in data if isinstance(item, int))
        return ids

    def _fetch_item(self, story_id: int) -> dict[str, Any] | None:
        data = self._fetch_json(HN_ITEM_URL.format(item_id=story_id))
        return data if isinstance(data, dict) else None

    def _fetch_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            data: bytes = response.read()
        return json.loads(data.decode("utf-8"))

    def _item_to_raw(
        self,
        item: dict[str, Any],
        *,
        fetched_at: datetime,
        cutoff: datetime | None,
    ) -> RawSourceItem | None:
        if item.get("deleted") is True or item.get("dead") is True:
            return None
        if item.get("type") != "story":
            return None
        item_id = item.get("id")
        title = item.get("title")
        if not isinstance(item_id, int) or not isinstance(title, str) or not title:
            return None
        published_at = _hn_time_to_datetime(item.get("time"))
        if cutoff is not None and published_at is not None and published_at < cutoff:
            return None
        score = _optional_int(item.get("score"))
        if (
            self.min_score is not None
            and score is not None
            and score < int(self.min_score)
        ):
            return None
        url = item.get("url")
        matched_keywords = self._matched_keywords(f"{title} {url or ''}")
        if self.keywords and not matched_keywords:
            return None
        if not isinstance(url, str) or not url:
            if not matched_keywords:
                return None
            url = HN_WEB_ITEM_URL.format(item_id=item_id)
        text = item.get("text")
        raw_text = text if isinstance(text, str) and text else title
        kids = item.get("kids")
        payload = {
            "id": item_id,
            "type": item.get("type"),
            "by": item.get("by"),
            "time": item.get("time"),
            "title": title,
            "url": item.get("url"),
            "score": item.get("score"),
            "descendants": item.get("descendants"),
            "kids_count": len(kids) if isinstance(kids, list) else 0,
        }
        return RawSourceItem(
            source=SourceType.HACKERNEWS,
            source_item_id=str(item_id),
            raw_url=canonicalize_url(url),
            raw_title=title,
            raw_text=raw_text,
            raw_payload=payload,
            fetched_at=fetched_at,
        )

    def _matched_keywords(self, text: str) -> list[str]:
        normalized = normalize_for_matching(text)
        matches = []
        for keyword in self.keywords:
            if normalize_for_matching(keyword) in normalized:
                matches.append(keyword)
        return matches

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


def _hn_time_to_datetime(value: Any) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
