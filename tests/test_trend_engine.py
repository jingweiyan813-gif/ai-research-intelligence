from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from airi.intelligence import TrendEngine
from airi.models import IntelligenceItem, ItemType, SourceType, TrendType
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item


def _state(tmp_path: Path) -> StateStore:
    return StateStore(StoragePaths.default(tmp_path))


def _fresh_item(**kwargs: Any) -> IntelligenceItem:
    return make_item(fetched_at=datetime.now(timezone.utc), **kwargs)


def test_ignores_items_without_topics(tmp_path: Path) -> None:
    engine = TrendEngine(_state(tmp_path))

    result = engine.analyze([make_item(topics=[])])

    assert result.analyzed_item_count == 0
    assert result.trends == []


def test_creates_topic_trend_counts_by_source_and_item_type(tmp_path: Path) -> None:
    items = [
        _fresh_item(item_id="p", topics=["coding_agents"], item_type=ItemType.PAPER),
        _fresh_item(
            item_id="r",
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
            topics=["coding_agents"],
        ),
        _fresh_item(
            item_id="h",
            source=SourceType.HACKERNEWS,
            item_type=ItemType.DISCUSSION,
            topics=["coding_agents"],
        ),
        _fresh_item(
            item_id="c",
            source=SourceType.COMPANY_BLOGS,
            item_type=ItemType.COMPANY_UPDATE,
            topics=["coding_agents"],
        ),
    ]

    trend = TrendEngine(_state(tmp_path)).analyze(items).trends[0]

    assert trend.item_count == 4
    assert trend.source_count == 4
    assert trend.paper_count == 1
    assert trend.repo_count == 1
    assert trend.hn_count == 1
    assert trend.company_count == 1


def test_growth_rate_from_stored_topic_timeseries(tmp_path: Path) -> None:
    state = _state(tmp_path)
    today = datetime.now(timezone.utc)
    state.save_topic_timeseries(
        {
            (today - timedelta(days=40)).date().isoformat(): {
                "ai_agents": {"item_count": 2}
            }
        }
    )
    items = [
        _fresh_item(item_id=str(index), topics=["ai_agents"])
        for index in range(4)
    ]

    trend = TrendEngine(state).analyze(items, window_days=30).trends[0]

    assert trend.previous_window_count == 2
    assert trend.growth_rate == 1.0


def test_classifies_emerging_accelerating_stable_declining_and_noise(
    tmp_path: Path,
) -> None:
    now = datetime.now(timezone.utc)
    state = _state(tmp_path)
    state.save_topic_timeseries(
        {
            (now - timedelta(days=40)).date().isoformat(): {
                "accelerating": {"item_count": 1},
                "stable": {"item_count": 2},
                "declining": {"item_count": 5},
            }
        }
    )
    items = [
        _fresh_item(item_id="e1", topics=["emerging"]),
        _fresh_item(item_id="e2", topics=["emerging"]),
        _fresh_item(item_id="a1", topics=["accelerating"]),
        _fresh_item(item_id="a2", topics=["accelerating"]),
        _fresh_item(item_id="s1", topics=["stable"]),
        _fresh_item(item_id="s2", topics=["stable"]),
        _fresh_item(item_id="d1", topics=["declining"]),
        _fresh_item(item_id="n1", topics=["noise"]),
    ]

    trends = {
        trend.topic: trend.trend_type
        for trend in TrendEngine(state).analyze(items).trends
    }

    assert trends["emerging"] == TrendType.EMERGING
    assert trends["accelerating"] == TrendType.ACCELERATING
    assert trends["stable"] == TrendType.STABLE
    assert trends["declining"] == TrendType.DECLINING
    assert trends["noise"] == TrendType.NOISE


def test_creates_trend_claim_with_evidence_ref(tmp_path: Path) -> None:
    items = [
        _fresh_item(item_id="a", topics=["ai_agents"]),
        _fresh_item(item_id="b", topics=["ai_agents"]),
    ]

    result = TrendEngine(_state(tmp_path)).analyze(items)

    assert len(result.claims) == 1
    assert result.claims[0].evidence_refs[0].item_id in {"a", "b"}
    assert result.claims[0].metrics["current_count"] == 2.0


def test_update_timeseries_preserves_existing_dates(tmp_path: Path) -> None:
    state = _state(tmp_path)
    old_date = "2026-01-01"
    state.save_topic_timeseries({old_date: {"old": {"item_count": 1}}})

    TrendEngine(state).update_timeseries(
        [make_item(item_id="a", topics=["ai_agents"])],
        as_of=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    saved = state.load_topic_timeseries()
    assert old_date in saved
    assert saved["2026-01-02"]["ai_agents"]["item_count"] == 1
