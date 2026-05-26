from __future__ import annotations

import pytest
from pydantic import ValidationError

from airi.models import ScoreBreakdown, ScoreBundle


def valid_score_bundle() -> ScoreBundle:
    return ScoreBundle(
        topic_relevance=0.8,
        quality=0.7,
        freshness=0.6,
        popularity=0.5,
        novelty=0.4,
        momentum=0.3,
        personal_relevance=0.9,
        cross_source_correlation=0.2,
        final_score=0.75,
        breakdowns=[
            ScoreBreakdown(dimension="quality", score=0.7, reason="Strong source.")
        ],
    )


def test_score_bundle_valid() -> None:
    scores = valid_score_bundle()

    assert scores.final_score == 0.75


def test_score_range_validation() -> None:
    with pytest.raises(ValidationError):
        ScoreBreakdown(dimension="quality", score=1.1, reason="Too high.")


def test_score_breakdown_empty_reason_fails() -> None:
    with pytest.raises(ValidationError):
        ScoreBreakdown(dimension="quality", score=0.8, reason="")
