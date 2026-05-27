from __future__ import annotations

from airi.rank import ItemRanker, ItemScorer, explain_score, summarize_top_items
from tests.factories import make_item

CONFIG = {"weights": {"topic_relevance": 1.0}}


def test_explain_score_lists_breakdowns() -> None:
    item = ItemRanker(ItemScorer(CONFIG), force=True).score_and_rank([make_item()])[0]

    explanation = explain_score(item)

    assert "Final score" in explanation
    assert "topic_relevance" in explanation


def test_explain_score_handles_unscored_item() -> None:
    assert "no score" in explain_score(make_item())


def test_summarize_top_items_plain_text() -> None:
    ranked = ItemRanker(ItemScorer(CONFIG), force=True).score_and_rank(
        [make_item(item_id="a"), make_item(item_id="b")]
    )

    summary = summarize_top_items(ranked, top=1)

    assert summary.startswith("1.")
    assert "AI Agent Paper" in summary
