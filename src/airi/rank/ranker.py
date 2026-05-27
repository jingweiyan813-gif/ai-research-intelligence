from __future__ import annotations

from airi.models import IntelligenceItem
from airi.rank.scorer import ItemScorer


class ItemRanker:
    def __init__(self, scorer: ItemScorer, *, force: bool = False) -> None:
        self.scorer = scorer
        self.force = force

    def rank(
        self,
        items: list[IntelligenceItem],
        top: int | None = None,
    ) -> list[IntelligenceItem]:
        ranked = sorted(items, key=self._sort_key)
        return ranked[:top] if top is not None else ranked

    def score_and_rank(
        self,
        items: list[IntelligenceItem],
        top: int | None = None,
    ) -> list[IntelligenceItem]:
        scored = []
        for item in items:
            if self.force or item.scores is None:
                item = item.model_copy(update={"scores": self.scorer.score(item)})
            scored.append(item)
        return self.rank(scored, top=top)

    def _sort_key(
        self,
        item: IntelligenceItem,
    ) -> tuple[float, float, float, float, str]:
        scores = item.scores
        final_score = scores.final_score if scores is not None else 0.0
        quality = scores.quality if scores is not None else 0.0
        freshness = scores.freshness if scores is not None else 0.0
        timestamp = (item.published_at or item.fetched_at).timestamp()
        return (-final_score, -quality, -freshness, -timestamp, item.title)
