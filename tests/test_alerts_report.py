from __future__ import annotations

from datetime import datetime, timezone

from airi.report import AlertsReportGenerator
from tests.factories import make_item


def test_alerts_report_handles_no_alerts() -> None:
    report = AlertsReportGenerator(
        alert_threshold=0.99,
        generated_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
    ).generate([make_item()], [])

    assert "# AI 技术情报提醒 - 2026-05-27" in report
    assert "暂无高信号提醒。" in report
