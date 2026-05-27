from __future__ import annotations

from datetime import datetime, timezone

from airi.intelligence import DedupeEngine
from airi.models import ItemType, SourceType
from tests.factories import make_item


def test_exact_id_duplicate_removed() -> None:
    items = [make_item(item_id="same"), make_item(item_id="same", title="Other")]

    result = DedupeEngine().dedupe(items)

    assert result.removed_count == 1
    assert result.duplicate_groups[0].reason == "exact id match"


def test_canonical_url_duplicate_removed() -> None:
    items = [
        make_item(item_id="a", canonical_url="https://example.com/a"),
        make_item(item_id="b", canonical_url="https://example.com/a"),
    ]

    result = DedupeEngine().dedupe(items)

    assert result.removed_count == 1
    assert result.duplicate_groups[0].reason == "canonical url match"


def test_content_fingerprint_duplicate_removed() -> None:
    items = [
        make_item(item_id="a", title="Same Title", abstract="Same body", url="https://a.test"),
        make_item(item_id="b", title=" Same  Title ", abstract="Same body", url="https://b.test"),
    ]

    result = DedupeEngine().dedupe(items)

    assert result.removed_count == 1
    assert result.duplicate_groups[0].reason == "content fingerprint match"


def test_github_owner_repo_duplicate_removed() -> None:
    items = [
        make_item(
            item_id="a",
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
            url="https://github.com/OpenAI/Codex/issues/1",
            canonical_url="https://github.com/OpenAI/Codex/issues/1",
        ),
        make_item(
            item_id="b",
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
            url="https://github.com/OpenAI/Codex/tree/main",
            canonical_url="https://github.com/OpenAI/Codex/tree/main",
        ),
    ]

    result = DedupeEngine().dedupe(items)

    assert result.removed_count == 1
    assert result.duplicate_groups[0].reason == "source-specific stable key match"


def test_representative_selection_prefers_richer_signals_and_newer_item() -> None:
    old_plain = make_item(
        item_id="old",
        canonical_url="https://example.com/a",
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    new_rich = make_item(
        item_id="new",
        canonical_url="https://example.com/a",
        fetched_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        github_signals=True,
    )

    result = DedupeEngine().dedupe([old_plain, new_rich])

    assert result.items[0].id == "new"
    assert result.duplicate_groups[0].representative_id == "new"
    assert result.duplicate_groups[0].duplicate_ids == ["old"]


def test_near_title_duplicate_preserves_reason() -> None:
    items = [
        make_item(item_id="a", title="New AI Agent Coding Tool", url="https://x.test/a"),
        make_item(item_id="b", title="New AI Agent Coding Tool", url="https://x.test/b"),
    ]

    result = DedupeEngine().dedupe(items)

    assert result.removed_count == 1
    assert result.duplicate_groups[0].confidence >= 0.9
