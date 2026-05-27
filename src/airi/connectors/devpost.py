from __future__ import annotations

import html
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from airi.connectors.base import BaseConnector
from airi.models import (
    CommonSignals,
    HackathonSignals,
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

USER_AGENT = "ai-research-intelligence"
_HACKATHON_LINK_RE = re.compile(
    r'href=["\'](?P<url>https?://[^"\']*devpost\.com/[^"\']+)["\']',
    re.I,
)
_TITLE_RE = re.compile(r'<h[1-4][^>]*>(?P<title>.*?)</h[1-4]>', re.I | re.S)
_DEADLINE_RE = re.compile(
    r'(?:deadline|submission deadline)[^<\n:]*[:\s]+'
    r'(?P<date>[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
    re.I,
)
_PRIZE_RE = re.compile(r'(?P<prize>\$[0-9][0-9,]*(?:\s+in\s+prizes?)?)', re.I)
_TAG_RE = re.compile(
    r'<(?:span|a)[^>]*(?:tag|theme)[^>]*>(?P<tag>.*?)</(?:span|a)>',
    re.I | re.S,
)


class DevpostConnector(BaseConnector):
    name = "devpost"
    source = SourceType.DEVPOST
    connector_version = "v1"

    def __init__(self, config: Any) -> None:
        self.config = config
        self.keywords = list(_get_config_value(config, "keywords", []))
        self.max_results = int(_get_config_value(config, "max_results", 30))
        self.days_ahead = _get_config_value(config, "days_ahead", None)
        self.listing_urls = list(_get_config_value(config, "listing_urls", []))
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
        fetched_at = datetime.now(timezone.utc)
        latest_deadline = self._latest_deadline(since)
        raw_items: list[RawSourceItem] = []
        seen_urls: set[str] = set()
        listing_urls = self.listing_urls or ["https://devpost.com/hackathons"]

        for listing_url in listing_urls:
            html_text = self._fetch_text(listing_url)
            for payload in self.parse_listing(html_text, listing_url=listing_url):
                raw_item = self._payload_to_raw(payload, fetched_at=fetched_at)
                if raw_item is None:
                    continue
                deadline = parse_devpost_datetime(raw_item.raw_payload.get("deadline"))
                if latest_deadline is not None and deadline is not None:
                    if deadline > latest_deadline:
                        continue
                matched_keywords = self._matched_keywords(
                    f"{raw_item.raw_title} {raw_item.raw_text or ''} "
                    f"{' '.join(_string_list(raw_item.raw_payload.get('tags')))}"
                )
                if self.keywords and not matched_keywords:
                    continue
                canonical = canonicalize_url(raw_item.raw_url)
                if canonical in seen_urls:
                    continue
                seen_urls.add(canonical)
                raw_item.raw_payload["matched_keywords"] = matched_keywords
                raw_items.append(raw_item)
                if len(raw_items) >= effective_limit:
                    return raw_items
        return raw_items

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        payload_hash = source_payload_hash(raw.raw_payload)
        title = normalize_text(raw.raw_title)
        snippet = normalize_text(raw.raw_text or "")
        canonical = canonicalize_url(raw.raw_url)
        tags = _string_list(raw.raw_payload.get("tags"))
        matched_keywords = _string_list(raw.raw_payload.get("matched_keywords"))
        deadline = parse_devpost_datetime(raw.raw_payload.get("deadline"))
        prize = raw.raw_payload.get("prize")
        is_remote = raw.raw_payload.get("is_remote")
        fetched_at = raw.fetched_at
        freshness_days = None
        if deadline is not None:
            freshness_days = max(0.0, (deadline - fetched_at).total_seconds() / 86400)

        return IntelligenceItem(
            id=build_item_id(SourceType.DEVPOST, canonical),
            source=SourceType.DEVPOST,
            item_type=ItemType.HACKATHON,
            title=title,
            url=canonical,
            canonical_url=canonical,
            abstract=snippet,
            content_snippet=compact_text(snippet, 280) if snippet else None,
            authors=[],
            organizations=[],
            repos=[],
            papers=[],
            published_at=deadline,
            fetched_at=fetched_at,
            topics=[],
            entities=[],
            keywords=tags + matched_keywords,
            source_metadata=SourceMetadata(
                source=SourceType.DEVPOST,
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
                    source_importance=0.5,
                ),
                hackathon=HackathonSignals(
                    deadline_at=deadline,
                    prize_amount=prize if isinstance(prize, str) else None,
                    is_remote=is_remote if isinstance(is_remote, bool) else None,
                ),
            ),
            source_payload_hash=payload_hash,
            content_fingerprint=content_fingerprint(title, snippet),
        )

    def _fetch_text(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            data: bytes = response.read()
        return data.decode("utf-8", errors="replace")

    def parse_listing(
        self,
        html_text: str,
        *,
        listing_url: str,
    ) -> list[dict[str, Any]]:
        cards = _split_cards(html_text)
        if not cards:
            cards = [html_text]
        payloads = []
        for card in cards:
            payload = self._parse_card(card, listing_url=listing_url)
            if payload is not None:
                payloads.append(payload)
        return payloads

    def _parse_card(self, card: str, *, listing_url: str) -> dict[str, Any] | None:
        link_match = _HACKATHON_LINK_RE.search(card)
        title_match = _TITLE_RE.search(card)
        if link_match is None or title_match is None:
            return None
        url = canonicalize_url(link_match.group("url"))
        title = normalize_text(_clean_html(title_match.group("title")))
        if not title:
            return None
        text = normalize_text(_clean_html(card))
        deadline_match = _DEADLINE_RE.search(text)
        prize_match = _PRIZE_RE.search(text)
        tags = [
            normalize_text(_clean_html(match.group("tag")))
            for match in _TAG_RE.finditer(card)
        ]
        tags = [tag for tag in tags if tag]
        matching_text = normalize_for_matching(text)
        is_remote = "remote" in matching_text or "online" in matching_text
        snippet = text[:500]
        return {
            "title": title,
            "url": url,
            "deadline": deadline_match.group("date") if deadline_match else None,
            "prize": prize_match.group("prize") if prize_match else None,
            "is_remote": is_remote,
            "tags": tags,
            "snippet": snippet,
            "listing_url": listing_url,
        }

    def _payload_to_raw(
        self,
        payload: dict[str, Any],
        *,
        fetched_at: datetime,
    ) -> RawSourceItem | None:
        title = payload.get("title")
        url = payload.get("url")
        if not isinstance(title, str) or not title:
            return None
        if not isinstance(url, str) or not url:
            return None
        canonical = canonicalize_url(url)
        snippet = payload.get("snippet")
        return RawSourceItem(
            source=SourceType.DEVPOST,
            source_item_id=canonical,
            raw_url=canonical,
            raw_title=title,
            raw_text=snippet if isinstance(snippet, str) else None,
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

    def _latest_deadline(self, since: datetime | None) -> datetime | None:
        if since is not None:
            return _ensure_timezone(since)
        if self.days_ahead is None:
            return None
        return datetime.now(timezone.utc) + timedelta(days=int(self.days_ahead))


def parse_devpost_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            try:
                parsed = datetime.strptime(value.replace(",", ""), "%B %d %Y")
            except ValueError:
                try:
                    parsed = datetime.strptime(value.replace(",", ""), "%b %d %Y")
                except ValueError:
                    return None
    return _ensure_timezone(parsed)


def _split_cards(html_text: str) -> list[str]:
    card_pattern = re.compile(
        r'<(?P<tag>div|article|li)[^>]*(?:hackathon|challenge|software-list-content)[^>]*>.*?</(?P=tag)>',
        re.I | re.S,
    )
    return [match.group(0) for match in card_pattern.finditer(html_text)]


def _clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(without_tags)


def _get_config_value(config: Any, name: str, default: Any) -> Any:
    if isinstance(config, dict):
        return config.get(name, default)
    return getattr(config, name, default)


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
