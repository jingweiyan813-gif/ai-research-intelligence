from __future__ import annotations

from datetime import datetime, timezone

from airi.intelligence import CrossSourceAnalyzer, PaperRepoLinker, TrendEngine
from airi.models import ItemType, SourceType
from airi.rank import ItemScorer
from airi.report import WeeklyReportGenerator
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item
from tests.test_scorer import SCORING_CONFIG


def _scored(item_id: str, **kwargs: object):  # type: ignore[no-untyped-def]
    item = make_item(item_id=item_id, fetched_at=datetime.now(timezone.utc), **kwargs)
    return item.model_copy(update={"scores": ItemScorer(SCORING_CONFIG).score(item)})


def test_weekly_report_contains_required_sections(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default(tmp_path))
    items = [
        _scored("p1", topics=["agents"], item_type=ItemType.PAPER),
        _scored(
            "r1",
            topics=["agents"],
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
        ),
    ]
    trends = TrendEngine(state).analyze(items)
    correlations = CrossSourceAnalyzer().analyze(items)
    links = PaperRepoLinker().link(items)

    report = WeeklyReportGenerator(
        generated_at=datetime(2026, 5, 27, tzinfo=timezone.utc)
    ).generate(items, trends, correlations, links)

    assert "# AI Research Intelligence Weekly Report - 2026-05-27" in report
    for section in [
        "Executive Summary",
        "Top Ranked Items",
        "Papers",
        "GitHub / DevTools",
        "Emerging Trends",
        "Cross-source Signals",
        "Paper-Repo Links",
        "Recommended Actions",
    ]:
        assert f"## {section}" in report


def test_weekly_report_is_deterministic(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default(tmp_path))
    items = [_scored("p1", topics=["agents"]), _scored("p2", topics=["agents"])]
    trends = TrendEngine(state).analyze(items)
    correlations = CrossSourceAnalyzer().analyze(items)

    generator = WeeklyReportGenerator(
        generated_at=datetime(2026, 5, 27, tzinfo=timezone.utc)
    )

    assert generator.generate(items, trends, correlations, []) == generator.generate(
        items,
        trends,
        correlations,
        [],
    )


def test_weekly_report_includes_top_ranked_items_and_evidence(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default(tmp_path))
    items = [_scored("p1", topics=["agents"]), _scored("p2", topics=["agents"])]
    trends = TrendEngine(state).analyze(items)

    report = WeeklyReportGenerator(
        generated_at=datetime(2026, 5, 27, tzinfo=timezone.utc)
    ).generate(items, trends, [], [])

    assert "1. score=" in report
    assert "Evidence:" in report
    assert "`p1`" in report or "`p2`" in report
