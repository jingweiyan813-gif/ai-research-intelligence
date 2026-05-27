from __future__ import annotations

import pytest
from pydantic import ValidationError

from airi.config.schema import ScoringConfig, SourcesConfig

PROFILE_WEIGHTS = {
    "topic_relevance": 0.22,
    "quality": 0.20,
    "momentum": 0.16,
    "cross_source_correlation": 0.16,
    "freshness": 0.10,
    "novelty": 0.08,
    "popularity": 0.04,
    "personal_relevance": 0.04,
}


def _scoring_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "active_profile": "intelligence",
        "ranking_profiles": {
            "item_baseline": {
                "topic_relevance": 0.30,
                "quality": 0.25,
                "freshness": 0.15,
                "novelty": 0.10,
                "popularity": 0.10,
                "personal_relevance": 0.10,
                "momentum": 0.00,
                "cross_source_correlation": 0.00,
            },
            "intelligence": PROFILE_WEIGHTS,
            "personal": {
                "topic_relevance": 0.24,
                "quality": 0.18,
                "personal_relevance": 0.18,
                "momentum": 0.14,
                "cross_source_correlation": 0.12,
                "freshness": 0.08,
                "novelty": 0.04,
                "popularity": 0.02,
            },
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
    payload.update(overrides)
    return payload


def test_ranking_profiles_sum_validation_works() -> None:
    config = ScoringConfig.model_validate(_scoring_payload())

    for profile in config.ranking_profiles.values():
        assert sum(profile.model_dump().values()) == pytest.approx(1.0)
    assert config.weights == config.ranking_profiles["intelligence"]


def test_active_profile_validation() -> None:
    with pytest.raises(ValidationError, match="active_profile"):
        ScoringConfig.model_validate(_scoring_payload(active_profile="missing"))


def test_invalid_scoring_weights_fail() -> None:
    invalid_profile = dict(PROFILE_WEIGHTS)
    invalid_profile["topic_relevance"] = 0.50
    payload = _scoring_payload(
        ranking_profiles={"intelligence": invalid_profile},
    )

    with pytest.raises(ValidationError, match="scoring weights must sum to 1.0"):
        ScoringConfig.model_validate(payload)


def test_legacy_flat_weights_are_migrated() -> None:
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

    assert config.active_profile == "item_baseline"
    assert config.weights.topic_relevance == 0.24


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
