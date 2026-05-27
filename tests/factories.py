from __future__ import annotations

from datetime import datetime, timezone

from airi.models import (
    CommonSignals,
    GitHubSignals,
    IntelligenceItem,
    ItemType,
    SignalBundle,
    SourceMetadata,
    SourceType,
)
from airi.normalize import content_fingerprint, source_payload_hash


def make_item(
    *,
    item_id: str = "item_1",
    source: SourceType = SourceType.ARXIV,
    item_type: ItemType = ItemType.PAPER,
    title: str = "AI Agent Paper",
    url: str = "https://example.com/item/1",
    canonical_url: str | None = None,
    abstract: str | None = "A paper about AI agents from OpenAI.",
    content_snippet: str | None = None,
    keywords: list[str] | None = None,
    entities: list[str] | None = None,
    topics: list[str] | None = None,
    repos: list[str] | None = None,
    papers: list[str] | None = None,
    fetched_at: datetime | None = None,
    published_at: datetime | None = None,
    source_item_id: str | None = None,
    github_signals: bool = False,
) -> IntelligenceItem:
    fetched = fetched_at or datetime(2026, 1, 1, tzinfo=timezone.utc)
    payload = {"id": source_item_id or item_id, "title": title, "url": url}
    payload_hash = source_payload_hash(payload)
    canonical = canonical_url or url
    signals = SignalBundle(common=CommonSignals(source_importance=0.5))
    if github_signals:
        signals = SignalBundle(
            common=CommonSignals(source_importance=0.5),
            github=GitHubSignals(stars=10),
        )
    return IntelligenceItem(
        id=item_id,
        source=source,
        item_type=item_type,
        title=title,
        url=url,
        canonical_url=canonical,
        abstract=abstract,
        content_snippet=content_snippet,
        repos=repos or [],
        papers=papers or [],
        published_at=published_at,
        fetched_at=fetched,
        topics=topics or [],
        entities=entities or [],
        keywords=keywords or [],
        source_metadata=SourceMetadata(
            source=source,
            source_item_id=source_item_id,
            source_url=canonical,
            fetched_at=fetched,
            connector_name=source.value,
            raw_payload_hash=payload_hash,
        ),
        signals=signals,
        source_payload_hash=payload_hash,
        content_fingerprint=content_fingerprint(title, abstract),
    )
