from __future__ import annotations

from airi.intelligence import CrossSourceAnalyzer
from airi.models import ItemType, SourceType
from airi.rank import ItemScorer
from tests.factories import make_item
from tests.test_scorer import SCORING_CONFIG


def test_detects_topic_across_multiple_source_categories() -> None:
    items = [
        make_item(item_id="p", topics=["agents"], item_type=ItemType.PAPER),
        make_item(
            item_id="r",
            topics=["agents"],
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
        ),
        make_item(
            item_id="h",
            topics=["agents"],
            source=SourceType.HACKERNEWS,
            item_type=ItemType.DISCUSSION,
        ),
    ]

    signal = CrossSourceAnalyzer().analyze(items)[0]

    assert signal.topic == "agents"
    assert signal.strength >= 0.8
    assert signal.sources == ["arxiv", "github", "hackernews"]


def test_strength_is_bounded() -> None:
    item = make_item(topics=["agents"])

    signal = CrossSourceAnalyzer().analyze([item])[0]

    assert 0.0 <= signal.strength <= 1.0


def test_apply_to_scores_updates_cross_source_correlation() -> None:
    scorer = ItemScorer(SCORING_CONFIG)
    items = [
        make_item(item_id="p", topics=["agents"]).model_copy(
            update={"scores": scorer.score(make_item(item_id="p", topics=["agents"]))}
        ),
        make_item(
            item_id="r",
            topics=["agents"],
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
        ).model_copy(
            update={
                "scores": scorer.score(
                    make_item(
                        item_id="r",
                        topics=["agents"],
                        source=SourceType.GITHUB,
                        item_type=ItemType.REPO,
                    )
                )
            }
        ),
    ]

    updated = CrossSourceAnalyzer(SCORING_CONFIG).apply_to_scores(items)

    assert updated[0].scores is not None
    assert updated[0].scores.cross_source_correlation == 0.5
    assert updated[0].scores.final_score >= 0.0


def test_output_ordering_is_deterministic() -> None:
    items = [make_item(item_id="b", topics=["b"]), make_item(item_id="a", topics=["a"])]

    topics = [signal.topic for signal in CrossSourceAnalyzer().analyze(items)]

    assert topics == ["a", "b"]
