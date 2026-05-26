from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from airi.models import EvidenceRef, SourceType, TopicTrend, TrendClaim, TrendType


def window() -> tuple[datetime, datetime]:
    start = datetime.now(timezone.utc)
    return start, start + timedelta(days=7)


def test_topic_trend_valid() -> None:
    start, end = window()
    trend = TopicTrend(
        topic="ai_agents",
        window_start=start,
        window_end=end,
        item_count=10,
        source_count=3,
        paper_count=4,
        repo_count=2,
        hn_count=3,
        company_count=1,
        previous_window_count=5,
        growth_rate=1.0,
        momentum_score=0.8,
        novelty_score=0.6,
        trend_type=TrendType.ACCELERATING,
        representative_item_ids=["item_abc"],
    )

    assert trend.item_count == 10


def test_topic_trend_window_validation() -> None:
    start, end = window()
    with pytest.raises(ValidationError, match="window_end must be after window_start"):
        TopicTrend(
            topic="ai_agents",
            window_start=end,
            window_end=start,
            item_count=10,
            source_count=3,
            paper_count=4,
            repo_count=2,
            hn_count=3,
            company_count=1,
            previous_window_count=5,
            growth_rate=1.0,
            momentum_score=0.8,
            novelty_score=0.6,
            trend_type=TrendType.ACCELERATING,
            representative_item_ids=["item_abc"],
        )


def test_trend_claim_requires_evidence_refs() -> None:
    start, end = window()
    with pytest.raises(ValidationError):
        TrendClaim(
            id="claim_1",
            topic="ai_agents",
            trend_type=TrendType.EMERGING,
            claim="Agents are emerging.",
            confidence=0.8,
            evidence_refs=[],
            window_start=start,
            window_end=end,
        )


def test_trend_claim_valid() -> None:
    start, end = window()
    claim = TrendClaim(
        id="claim_1",
        topic="ai_agents",
        trend_type=TrendType.EMERGING,
        claim="Agents are emerging.",
        confidence=0.8,
        evidence_refs=[
            EvidenceRef(
                item_id="item_abc",
                source=SourceType.ARXIV,
                title="Paper",
                url="https://arxiv.org/abs/1234",
            )
        ],
        window_start=start,
        window_end=end,
        metrics={"growth_rate": 1.2},
    )

    assert claim.evidence_refs[0].item_id == "item_abc"


def test_trend_claim_rejects_non_finite_metric() -> None:
    start, end = window()
    with pytest.raises(ValidationError, match="metric values must be finite"):
        TrendClaim(
            id="claim_1",
            topic="ai_agents",
            trend_type=TrendType.EMERGING,
            claim="Agents are emerging.",
            confidence=0.8,
            evidence_refs=[
                EvidenceRef(
                    item_id="item_abc",
                    source=SourceType.ARXIV,
                    title="Paper",
                    url="https://arxiv.org/abs/1234",
                )
            ],
            window_start=start,
            window_end=end,
            metrics={"growth_rate": float("inf")},
        )
