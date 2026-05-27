from __future__ import annotations

import json
import urllib.parse
import urllib.request
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
    canonicalize_url,
    compact_text,
    content_fingerprint,
    normalize_text,
    source_payload_hash,
)

OPENREVIEW_NOTES_URL = "https://api2.openreview.net/notes"
OPENREVIEW_FORUM_URL = "https://openreview.net/forum?id={note_id}"
USER_AGENT = "ai-research-intelligence"


class OpenReviewConnector(BaseConnector):
    name = "openreview"
    source = SourceType.OPENREVIEW
    connector_version = "v1"

    def __init__(self, config: Any) -> None:
        self.config = config
        self.venues = list(_get_config_value(config, "venues", []))
        self.queries = list(_get_config_value(config, "queries", []))
        self.max_results = int(_get_config_value(config, "max_results", 50))
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

        for url in self.build_query_urls(limit=effective_limit):
            response = self._fetch_json(url)
            notes = response.get("notes", [])
            if not isinstance(notes, list):
                continue
            for note in notes:
                if not isinstance(note, dict):
                    continue
                raw_item = self._note_to_raw(note, fetched_at=fetched_at)
                if raw_item is None:
                    continue
                published_at = _timestamp_to_datetime(
                    raw_item.raw_payload.get("cdate")
                    or raw_item.raw_payload.get("mdate")
                )
                if (
                    cutoff is not None
                    and published_at is not None
                    and published_at < cutoff
                ):
                    continue
                stable_key = raw_item.source_item_id or raw_item.raw_url
                if stable_key in seen_ids:
                    continue
                seen_ids.add(stable_key)
                raw_items.append(raw_item)
                if len(raw_items) >= effective_limit:
                    return raw_items
        return raw_items

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        payload_hash = source_payload_hash(raw.raw_payload)
        title = normalize_text(raw.raw_title)
        abstract = normalize_text(raw.raw_text or "")
        canonical = canonicalize_url(raw.raw_url)
        note_id = raw.source_item_id or canonical
        keywords = _string_list(raw.raw_payload.get("keywords"))
        authors = _string_list(raw.raw_payload.get("authors"))
        venue = raw.raw_payload.get("venue")
        venue_text = venue if isinstance(venue, str) and venue else None
        published_at = _timestamp_to_datetime(
            raw.raw_payload.get("cdate") or raw.raw_payload.get("mdate")
        )
        fetched_at = raw.fetched_at
        freshness_days = None
        if published_at is not None:
            freshness_days = max(
                0.0,
                (fetched_at - published_at).total_seconds() / 86400,
            )

        return IntelligenceItem(
            id=build_item_id(SourceType.OPENREVIEW, note_id),
            source=SourceType.OPENREVIEW,
            item_type=ItemType.PAPER,
            title=title,
            url=canonical,
            canonical_url=canonical,
            abstract=abstract,
            content_snippet=compact_text(abstract, 280) if abstract else None,
            authors=authors,
            organizations=[],
            repos=[],
            papers=[note_id] if note_id else [],
            published_at=published_at,
            fetched_at=fetched_at,
            topics=[],
            entities=[],
            keywords=keywords,
            source_metadata=SourceMetadata(
                source=SourceType.OPENREVIEW,
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
                    source_importance=0.7,
                ),
                paper=PaperSignals(venue=venue_text, paper_categories=keywords),
            ),
            source_payload_hash=payload_hash,
            content_fingerprint=content_fingerprint(title, abstract),
        )

    def build_query_urls(self, *, limit: int | None = None) -> list[str]:
        effective_limit = limit if limit is not None else self.max_results
        urls = []
        for venue in self.venues:
            urls.append(self._build_notes_url(invitation=venue, limit=effective_limit))
        for query in self.queries:
            urls.append(self._build_notes_url(search=query, limit=effective_limit))
        if not urls:
            urls.append(self._build_notes_url(search="agent", limit=effective_limit))
        return urls

    def _build_notes_url(
        self,
        *,
        invitation: str | None = None,
        search: str | None = None,
        limit: int,
    ) -> str:
        params = {"limit": str(limit)}
        if invitation:
            params["invitation"] = invitation
        if search:
            params["term"] = search
        return f"{OPENREVIEW_NOTES_URL}?{urllib.parse.urlencode(params)}"

    def _fetch_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            data: bytes = response.read()
        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def _note_to_raw(
        self,
        note: dict[str, Any],
        *,
        fetched_at: datetime,
    ) -> RawSourceItem | None:
        note_id = note.get("id")
        if not isinstance(note_id, str) or not note_id:
            return None
        note_content = note.get("content")
        content: dict[str, Any] = note_content if isinstance(note_content, dict) else {}
        title = _content_value(content, "title")
        if not title:
            return None
        abstract = _content_value(content, "abstract")
        forum = note.get("forum") if isinstance(note.get("forum"), str) else note_id
        venue = _content_value(content, "venue") or _venue_from_note(note)
        keywords = _content_list(content, "keywords")
        authors = _content_list(content, "authors")
        payload: dict[str, Any] = {
            "id": note_id,
            "forum": forum,
            "venue": venue,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "keywords": keywords,
            "cdate": note.get("cdate"),
            "mdate": note.get("mdate"),
            "content": content,
        }
        url = OPENREVIEW_FORUM_URL.format(note_id=forum or note_id)
        return RawSourceItem(
            source=SourceType.OPENREVIEW,
            source_item_id=note_id,
            raw_url=canonicalize_url(url),
            raw_title=title,
            raw_text=abstract,
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


def _content_value(content: dict[str, Any], key: str) -> str:
    value = content.get(key)
    if isinstance(value, dict):
        nested = value.get("value")
        return nested if isinstance(nested, str) else ""
    return value if isinstance(value, str) else ""


def _content_list(content: dict[str, Any], key: str) -> list[str]:
    value = content.get(key)
    if isinstance(value, dict):
        value = value.get("value")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _venue_from_note(note: dict[str, Any]) -> str | None:
    invitations = note.get("invitations")
    if isinstance(invitations, list):
        for invitation in invitations:
            if isinstance(invitation, str) and invitation:
                return invitation
    return None


def _timestamp_to_datetime(value: Any) -> datetime | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return None


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
