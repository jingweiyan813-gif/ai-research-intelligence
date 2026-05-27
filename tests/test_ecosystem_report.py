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

    assert "# AI 生态雷达 - 2026-05-27" in report
    assert "## GitHub / DevTools 项目" in report
    assert "## 社区信号" in report
    assert "## 跨源信号" in report
    assert "## 执行摘要" not in report
    assert "## 论文" not in report
