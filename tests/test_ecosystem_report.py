from __future__ import annotations

from datetime import datetime, timezone

from airi.intelligence import CrossSourceAnalyzer, PaperRepoLinker
from airi.models import ItemType, SourceType
from airi.rank import ItemScorer
from airi.report import EcosystemReportGenerator
from tests.factories import make_item
from tests.test_scorer import SCORING_CONFIG


def _item(item_id: str, **kwargs: object):  # type: ignore[no-untyped-def]
    item = make_item(item_id=item_id, **kwargs)
    return item.model_copy(update={"scores": ItemScorer(SCORING_CONFIG).score(item)})


def test_ecosystem_report_focuses_on_ecosystem_sections() -> None:
    items = [
        _item(
            "repo",
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
            topics=["agents"],
        ),
        _item(
            "hn",
            source=SourceType.HACKERNEWS,
            item_type=ItemType.DISCUSSION,
            topics=["agents"],
        ),
    ]

    report = EcosystemReportGenerator(
        generated_at=datetime(2026, 5, 27, tzinfo=timezone.utc)
    ).generate(
        items,
        CrossSourceAnalyzer().analyze(items),
        PaperRepoLinker().link(items),
    )

    assert "# AI Research Ecosystem Report - 2026-05-27" in report
    assert "## GitHub / DevTools" in report
    assert "## Community Signals" in report
    assert "## Cross-source Signals" in report
    assert "## Executive Summary" not in report
    assert "## Papers" not in report
