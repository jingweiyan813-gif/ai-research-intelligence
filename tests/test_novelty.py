from __future__ import annotations

from airi.intelligence import NoveltyTracker
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item


def test_unseen_item_novelty_is_high(tmp_path) -> None:  # type: ignore[no-untyped-def]
    tracker = NoveltyTracker(StateStore(StoragePaths.default(tmp_path)))
    item = make_item(item_id="new")

    result = tracker.compute([item])["new"]

    assert result.novelty_score == 1.0
    assert result.seen_before is False


def test_seen_id_novelty_is_low(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default(tmp_path))
    item = make_item(item_id="seen")
    NoveltyTracker(state).update_seen([item])

    result = NoveltyTracker(state).compute([item])["seen"]

    assert result.novelty_score == 0.0
    assert result.seen_before is True


def test_seen_fingerprint_novelty_is_low(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default(tmp_path))
    original = make_item(item_id="original", title="Same", abstract="Body")
    NoveltyTracker(state).update_seen([original])
    candidate = make_item(item_id="candidate", title="Same", abstract="Body", url="https://x.test")

    result = NoveltyTracker(state).compute([candidate])["candidate"]

    assert result.novelty_score == 0.1
    assert result.reason == "content fingerprint seen before"


def test_compute_is_read_only(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default(tmp_path))
    tracker = NoveltyTracker(state)

    tracker.compute([make_item(item_id="x")])

    assert state.load_seen_items() == {}


def test_update_seen_writes_expected_state_and_increments(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default(tmp_path))
    tracker = NoveltyTracker(state)
    item = make_item(item_id="x")

    tracker.update_seen([item])
    tracker.update_seen([item])

    seen = state.load_seen_items()["x"]
    assert seen["item_id"] == "x"
    assert seen["canonical_url"] == item.canonical_url
    assert seen["content_fingerprint"] == item.content_fingerprint
    assert seen["seen_count"] == 2
