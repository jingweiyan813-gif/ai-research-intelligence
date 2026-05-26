from __future__ import annotations

import pytest
from pydantic import ValidationError

from airi.config.schema import ScoringConfig, SourcesConfig


def test_scoring_weights_sum_validation_works() -> None:
    config = ScoringConfig.model_validate(
        {
            "weights": {
                "topic_relevance": 0.24,
                "quality": 0.18,
                "momentum": 0.14,
                "novelty": 0.14,
                "freshness": 0.10,
                "popularity": 0.08,
                "personal_relevance": 0.12,
            },
            "thresholds": {
                "minimum_score": 0.35,
                "strong_signal": 0.70,
                "trend_candidate": 0.60,
            },
            "limits": {
                "max_items_per_source": 50,
                "max_report_items": 20,
                "max_trend_candidates": 30,
            },
        }
    )

    assert config.weights.topic_relevance == 0.24


def test_invalid_scoring_weights_fail() -> None:
    with pytest.raises(ValidationError, match="scoring weights must sum to 1.0"):
        ScoringConfig.model_validate(
            {
                "weights": {
                    "topic_relevance": 0.50,
                    "quality": 0.18,
                    "momentum": 0.14,
                    "novelty": 0.14,
                    "freshness": 0.10,
                    "popularity": 0.08,
                    "personal_relevance": 0.12,
                },
                "thresholds": {
                    "minimum_score": 0.35,
                    "strong_signal": 0.70,
                    "trend_candidate": 0.60,
                },
                "limits": {
                    "max_items_per_source": 50,
                    "max_report_items": 20,
                    "max_trend_candidates": 30,
                },
            }
        )


def test_at_least_one_enabled_source_is_required() -> None:
    with pytest.raises(ValidationError, match="at least one enabled source"):
        SourcesConfig.model_validate(
            {
                "sources": [
                    {
                        "id": "arxiv",
                        "name": "arXiv",
                        "enabled": False,
                        "type": "paper_preprint",
                    }
                ]
            }
        )
