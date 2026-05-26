from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from airi.models import (
    ExtractionMetadata,
    ExtractionMethod,
    IntelligenceItem,
    ItemType,
    SignalBundle,
    SourceMetadata,
    SourceType,
    build_item_id,
)


def source_metadata(source: SourceType = SourceType.ARXIV) -> SourceMetadata:
    return SourceMetadata(
        source=source,
        source_url="https://arxiv.org/abs/1234",
        fetched_at=datetime.now(timezone.utc),
        connector_name="arxiv",
        raw_payload_hash="payloadhash",
    )


def test_intelligence_item_valid_and_deduplicates_fields() -> None:
    item = IntelligenceItem(
        id="item_abc",
        source=SourceType.ARXIV,
        item_type=ItemType.PAPER,
        title="  A Paper  ",
        url="https://arxiv.org/abs/1234",
        fetched_at=datetime.now(timezone.utc),
        topics=["agents", "memory", "agents"],
        entities=["OpenAI", "OpenAI", "Anthropic"],
        keywords=["agent", "agent", "memory"],
        source_metadata=source_metadata(),
        extraction_metadata=[
            ExtractionMetadata(
                method=ExtractionMethod.RULE,
                extractor_name="rules",
                extractor_version="v1",
                extracted_at=datetime.now(timezone.utc),
            )
        ],
        signals=SignalBundle(),
        source_payload_hash="payloadhash",
        content_fingerprint="fingerprint",
    )

    assert item.title == "A Paper"
    assert item.topics == ["agents", "memory"]
    assert item.entities == ["OpenAI", "Anthropic"]
    assert item.keywords == ["agent", "memory"]


def test_build_item_id_is_stable() -> None:
    first = build_item_id(SourceType.ARXIV, "https://arxiv.org/abs/1234")
    second = build_item_id(SourceType.ARXIV, "https://arxiv.org/abs/1234")

    assert first == second
    assert first.startswith("item_")
    assert len(first) == 17


def test_source_metadata_source_must_match_item_source() -> None:
    with pytest.raises(
        ValidationError,
        match="source_metadata.source must match source",
    ):
        IntelligenceItem(
            id="item_abc",
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
            title="Repo",
            url="https://github.com/example/repo",
            fetched_at=datetime.now(timezone.utc),
            source_metadata=source_metadata(SourceType.ARXIV),
            signals=SignalBundle(),
            source_payload_hash="payloadhash",
            content_fingerprint="fingerprint",
        )


def test_intelligence_item_empty_required_field_fails() -> None:
    with pytest.raises(ValidationError):
        IntelligenceItem(
            id="",
            source=SourceType.ARXIV,
            item_type=ItemType.PAPER,
            title="Paper",
            url="https://arxiv.org/abs/1234",
            fetched_at=datetime.now(timezone.utc),
            source_metadata=source_metadata(),
            signals=SignalBundle(),
            source_payload_hash="payloadhash",
            content_fingerprint="fingerprint",
        )
