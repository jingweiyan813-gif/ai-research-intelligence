from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from airi.models import (
    CommonSignals,
    CommunitySignals,
    CompanySignals,
    GitHubSignals,
    ItemType,
    SignalBundle,
    SourceType,
)
from airi.rank import ItemScorer
from tests.factories import make_item

SCORING_CONFIG = {
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
        "intelligence": {
            "topic_relevance": 0.22,
            "quality": 0.20,
            "momentum": 0.16,
            "cross_source_correlation": 0.16,
            "freshness": 0.10,
            "novelty": 0.08,
            "popularity": 0.04,
            "personal_relevance": 0.04,
        },
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
    "freshness_half_life_days": 30,
}


def scorer(profile=None) -> ItemScorer:  # type: ignore[no-untyped-def]
    return ItemScorer(SCORING_CONFIG, profile)


def test_final_score_uses_configured_weights() -> None:
    item = make_item(topics=["ai_agents"], keywords=["ai_agents"])

    scores = scorer({"profile": {"interests": ["ai_agents"]}}).score(item)

    expected = sum(
        SCORING_CONFIG["ranking_profiles"]["intelligence"][dimension]
        * getattr(scores, dimension)
        for dimension in SCORING_CONFIG["ranking_profiles"]["intelligence"]
    )
    assert math.isclose(scores.final_score, expected)
    assert any(breakdown.dimension == "final_score" for breakdown in scores.breakdowns)


def test_scores_are_clamped_between_zero_and_one() -> None:
    item = make_item(
        source=SourceType.GITHUB,
        item_type=ItemType.REPO,
        topics=["a", "b", "c", "d", "e"],
    ).model_copy(
        update={
            "signals": SignalBundle(
                common=CommonSignals(),
                github=GitHubSignals(stars=10_000_000, forks=1_000_000),
            )
        }
    )

    scores = scorer().score(item)

    for value in scores.model_dump(exclude={"breakdowns"}).values():
        assert 0.0 <= value <= 1.0


def test_topic_relevance_increases_with_topics() -> None:
    empty = scorer().score(make_item(topics=[]))
    topical = scorer().score(make_item(topics=["ai_agents", "coding_agents"]))

    assert topical.topic_relevance > empty.topic_relevance


def test_github_stars_affect_quality_and_popularity() -> None:
    low = make_item(source=SourceType.GITHUB, item_type=ItemType.REPO).model_copy(
        update={
            "signals": SignalBundle(
                common=CommonSignals(),
                github=GitHubSignals(stars=1),
            )
        }
    )
    high = make_item(source=SourceType.GITHUB, item_type=ItemType.REPO).model_copy(
        update={
            "signals": SignalBundle(
                common=CommonSignals(),
                github=GitHubSignals(stars=5000),
            )
        }
    )

    low_scores = scorer().score(low)
    high_scores = scorer().score(high)

    assert high_scores.quality > low_scores.quality
    assert high_scores.popularity > low_scores.popularity


def test_hn_score_affects_popularity() -> None:
    item = make_item(item_type=ItemType.DISCUSSION).model_copy(
        update={
            "signals": SignalBundle(
                common=CommonSignals(),
                community=CommunitySignals(hn_score=100, hn_comments=50),
            )
        }
    )

    assert scorer().score(item).popularity > 0.2


def test_official_company_update_affects_quality() -> None:
    item = make_item(item_type=ItemType.COMPANY_UPDATE).model_copy(
        update={
            "signals": SignalBundle(
                common=CommonSignals(),
                company=CompanySignals(
                    company_name="OpenAI",
                    is_official_announcement=True,
                ),
            )
        }
    )

    assert scorer().score(item).quality >= 0.7


def test_freshness_decays_for_old_items() -> None:
    fresh = make_item().model_copy(update={"published_at": datetime.now(timezone.utc)})
    old = make_item().model_copy(
        update={"published_at": datetime.now(timezone.utc) - timedelta(days=365)}
    )

    assert scorer().score(fresh).freshness > scorer().score(old).freshness


def test_personal_relevance_matches_profile_interests() -> None:
    item = make_item(title="AI agent system", topics=["ai_agents"])

    scores = scorer({"profile": {"interests": ["ai_agents", "agent"]}}).score(item)

    assert scores.personal_relevance > 0.2


def test_scorer_can_use_named_ranking_profile() -> None:
    item = make_item(topics=["ai_agents"])

    baseline = ItemScorer(SCORING_CONFIG, ranking_profile="item_baseline").score(item)
    intelligence = ItemScorer(
        SCORING_CONFIG,
        ranking_profile="intelligence",
    ).score(item)

    assert baseline.final_score != intelligence.final_score


def test_invalid_ranking_profile_fails_clearly() -> None:
    item = make_item(topics=["ai_agents"])

    try:
        ItemScorer(SCORING_CONFIG, ranking_profile="missing").score(item)
    except ValueError as exc:
        assert "Unknown ranking profile" in str(exc)
    else:
        raise AssertionError("invalid profile should fail")
