from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from airi.connectors.base import ConnectorResult
from airi.connectors.rss import RSSConnector, parse_feed_datetime
from airi.models import (
    CommonSignals,
    CompanySignals,
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
    compact_text,
    content_fingerprint,
    normalize_for_matching,
    normalize_text,
    source_payload_hash,
)


class CompanyBlogsConnector(RSSConnector):
    name = "company_blogs"
    source = SourceType.COMPANY_BLOGS
    connector_version = "v1"

    def __init__(self, config: Any) -> None:
        self.config = config
        self.feeds = list(_get_config_value(config, "feeds", []))
        self.keywords = list(_get_config_value(config, "keywords", []))
        self.freshness_days = _get_config_value(config, "freshness_days", None)
        self.max_results = int(_get_config_value(config, "max_results", 20))
        self.enabled = bool(_get_config_value(config, "enabled", True))
        super().__init__(feeds=self.feeds)

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
        seen_urls: set[str] = set()
        self._feed_errors: list[str] = []

        for feed in self.feeds:
            feed_name = feed.get("name") or "Company Feed"
            feed_url = feed.get("url")
            if not feed_url:
                continue
            try:
                feed_text = self._fetch_feed_text(feed_url)
                feed_items = self.parse_feed(
                    feed_text,
                    feed_name=feed_name,
                    feed_url=feed_url,
                    fetched_at=fetched_at,
                )
            except Exception as exc:  # noqa: BLE001
                self._feed_errors.append(f"feed {feed_name} failed: {exc}")
                continue
            for item in feed_items:
                item.raw_payload["feed_name"] = feed_name
                published_at = _published_datetime(item.raw_payload)
                if (
                    cutoff is not None
                    and published_at is not None
                    and published_at < cutoff
                ):
                    continue
                matched_keywords = self._matched_keywords(
                    f"{item.raw_title} {item.raw_text or ''}"
                )
                if self.keywords and not matched_keywords:
                    continue
                canonical = canonicalize_url(item.raw_url)
                if canonical in seen_urls:
                    continue
                seen_urls.add(canonical)
                item.source = SourceType.COMPANY_BLOGS
                item.source_item_id = item.source_item_id or canonical
                item.raw_url = canonical
                item.raw_payload["matched_keywords"] = matched_keywords
                raw_items.append(item)
                if len(raw_items) >= effective_limit:
                    return raw_items
        return raw_items

    def fetch_and_normalize(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> tuple[list[IntelligenceItem], ConnectorResult]:
        items, result = super().fetch_and_normalize(since=since, limit=limit)
        result.errors.extend(getattr(self, "_feed_errors", []))
        return items, result

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        payload_hash = source_payload_hash(raw.raw_payload)
        title = normalize_text(raw.raw_title)
        summary = normalize_text(raw.raw_text or "")
        canonical = canonicalize_url(raw.raw_url)
        feed_name = str(raw.raw_payload.get("feed_name") or "Company Feed")
        tags = _string_list(raw.raw_payload.get("tags"))
        matched_keywords = _string_list(raw.raw_payload.get("matched_keywords"))
        published_at = _published_datetime(raw.raw_payload)
        fetched_at = raw.fetched_at
        freshness_days = None
        if published_at is not None:
            freshness_days = max(
                0.0,
                (fetched_at - published_at).total_seconds() / 86400,
            )

        return IntelligenceItem(
            id=build_item_id(SourceType.COMPANY_BLOGS, canonical),
            source=SourceType.COMPANY_BLOGS,
            item_type=ItemType.COMPANY_UPDATE,
            title=title,
            url=canonical,
            canonical_url=canonical,
            abstract=summary,
            content_snippet=compact_text(summary, 280) if summary else None,
            authors=[],
            organizations=[feed_name],
            repos=[],
            papers=[],
            published_at=published_at,
            fetched_at=fetched_at,
            topics=[],
            entities=[],
            keywords=tags + matched_keywords,
            source_metadata=SourceMetadata(
                source=SourceType.COMPANY_BLOGS,
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
                    source_importance=0.75,
                ),
                company=CompanySignals(
                    company_name=feed_name,
                    is_official_announcement=True,
                ),
            ),
            source_payload_hash=payload_hash,
            content_fingerprint=content_fingerprint(title, summary),
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


def _published_datetime(payload: dict[str, Any]) -> datetime | None:
    return parse_feed_datetime(payload.get("published")) or parse_feed_datetime(
        payload.get("updated")
    )


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
