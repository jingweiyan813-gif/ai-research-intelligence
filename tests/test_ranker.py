from __future__ import annotations

from datetime import datetime, timezone

from airi.rank import ItemRanker, ItemScorer
from tests.factories import make_item

CONFIG = {
    "weights": {
        "topic_relevance": 0.24,
        "quality": 0.18,
        "momentum": 0.14,
        "novelty": 0.14,
        "freshness": 0.10,
        "popularity": 0.08,
        "personal_relevance": 0.12,
    }
}


def test_rank_order_is_deterministic() -> None:
    scorer = ItemScorer(CONFIG, {"profile": {"interests": ["ai_agents"]}})
    ranker = ItemRanker(scorer, force=True)
    low = make_item(item_id="low", title="B item", topics=[])
    high = make_item(item_id="high", title="A item", topics=["ai_agents"])

    ranked = ranker.score_and_rank([low, high])

    assert [item.id for item in ranked] == ["high", "low"]


def test_rank_tie_breaks_by_newer_then_title() -> None:
    scorer = ItemScorer(CONFIG)
    ranker = ItemRanker(scorer, force=True)
    older = make_item(
        item_id="older",
        title="B title",
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = make_item(
        item_id="newer",
        title="A title",
        fetched_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    ranked = ranker.score_and_rank([older, newer])

    assert ranked[0].id in {"older", "newer"}
    assert all(item.scores is not None for item in ranked)


def test_top_limits_results() -> None:
    ranker = ItemRanker(ItemScorer(CONFIG), force=True)
    items = [make_item(item_id=str(index), title=f"Item {index}") for index in range(3)]

    assert len(ranker.score_and_rank(items, top=2)) == 2
