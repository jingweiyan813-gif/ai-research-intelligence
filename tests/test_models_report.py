from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from airi.models import Report, ReportSection


def test_report_valid() -> None:
    report = Report(
        title="Weekly AI Intelligence",
        generated_at=datetime.now(timezone.utc),
        report_type="weekly",
        sections=[
            ReportSection(
                title="Top Signals",
                content="Several agent projects accelerated.",
                evidence_item_ids=["item_abc"],
            )
        ],
        top_item_ids=["item_abc"],
        trend_claim_ids=["claim_1"],
    )

    assert report.sections[0].title == "Top Signals"


def test_report_requires_at_least_one_section() -> None:
    with pytest.raises(ValidationError):
        Report(
            title="Weekly AI Intelligence",
            generated_at=datetime.now(timezone.utc),
            report_type="weekly",
            sections=[],
        )


def test_report_empty_title_fails() -> None:
    with pytest.raises(ValidationError):
        Report(
            title="",
            generated_at=datetime.now(timezone.utc),
            report_type="weekly",
            sections=[ReportSection(title="Top Signals", content="Content")],
        )
