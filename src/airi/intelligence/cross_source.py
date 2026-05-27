from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from airi.models import (
    IntelligenceItem,
    ItemType,
    ScoreBreakdown,
    ScoreBundle,
    SourceType,
)
from airi.rank.scorer import resolve_scoring_weights


class CrossSourceSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    sources: list[str]
    item_ids: list[str]
    strength: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class CrossSourceAnalyzer:
    def __init__(self, scoring_config: Any | None = None) -> None:
        self.weights = _weights_from_config(scoring_config) if scoring_config else None

    def analyze(self, items: list[IntelligenceItem]) -> list[CrossSourceSignal]:
        by_topic: dict[str, list[IntelligenceItem]] = defaultdict(list)
        for item in items:
            for topic in item.topics:
                by_topic[topic].append(item)

        signals = []
        for topic, topic_items in sorted(by_topic.items()):
            sources = sorted({item.source.value for item in topic_items})
            categories = sorted({_source_category(item) for item in topic_items})
            strength = _strength_for_categories(len(categories))
            signals.append(
                CrossSourceSignal(
                    topic=topic,
                    sources=sources,
                    item_ids=sorted(item.id for item in topic_items),
                    strength=strength,
                    reason=(
                        f"Topic appears across {len(categories)} source categories: "
                        f"{', '.join(categories)}."
                    ),
                )
            )
        return signals

    def apply_to_scores(self, items: list[IntelligenceItem]) -> list[IntelligenceItem]:
        signals_by_topic = {signal.topic: signal for signal in self.analyze(items)}
        updated = []
        for item in items:
            if item.scores is None:
                updated.append(item)
                continue
            strength = max(
                (
                    signals_by_topic[topic].strength
                    for topic in item.topics
                    if topic in signals_by_topic
                ),
                default=0.0,
            )
            scores = _update_correlation_score(item, strength, self.weights)
            updated.append(item.model_copy(update={"scores": scores}))
        return updated


def _update_correlation_score(
    item: IntelligenceItem,
    strength: float,
    weights: dict[str, float] | None,
) -> ScoreBundle:
    if item.scores is None:
        raise ValueError("item must have scores")
    breakdowns = [
        breakdown
        for breakdown in item.scores.breakdowns
        if breakdown.dimension not in {"cross_source_correlation", "final_score"}
    ]
    breakdowns.append(
        ScoreBreakdown(
            dimension="cross_source_correlation",
            score=strength,
            reason=f"Deterministic cross-source topic signal strength {strength:.2f}.",
            evidence_item_ids=[item.id],
        )
    )
    final_score = item.scores.final_score
    if weights is not None:
        final_score = _weighted_final(item.scores, strength, weights)
        breakdowns.append(
            ScoreBreakdown(
                dimension="final_score",
                score=final_score,
                reason="Weighted sum after cross-source correlation update.",
                evidence_item_ids=[item.id],
            )
        )
    return item.scores.model_copy(
        update={
            "cross_source_correlation": strength,
            "final_score": final_score,
            "breakdowns": breakdowns,
        }
    )


def _weighted_final(
    scores: ScoreBundle,
    cross_source_correlation: float,
    weights: dict[str, float],
) -> float:
    values = scores.model_copy(
        update={"cross_source_correlation": cross_source_correlation}
    )
    total = 0.0
    for dimension, weight in weights.items():
        if hasattr(values, dimension):
            total += float(weight) * float(getattr(values, dimension))
    return _clamp(total)


def _source_category(item: IntelligenceItem) -> str:
    if item.item_type == ItemType.PAPER:
        return "papers"
    if item.item_type == ItemType.REPO:
        return "repos"
    if item.source == SourceType.HACKERNEWS or item.item_type == ItemType.DISCUSSION:
        return "community"
    if (
        item.source == SourceType.COMPANY_BLOGS
        or item.item_type == ItemType.COMPANY_UPDATE
    ):
        return "company"
    if item.item_type == ItemType.HACKATHON:
        return "hackathon"
    return str(item.source.value)


def _strength_for_categories(category_count: int) -> float:
    if category_count <= 1:
        return 0.1
    if category_count == 2:
        return 0.5
    return min(1.0, 0.8 + (category_count - 3) * 0.05)


def _weights_from_config(scoring_config: Any) -> dict[str, float]:
    return resolve_scoring_weights(scoring_config)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
