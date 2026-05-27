from __future__ import annotations

from pathlib import Path

from airi.cli import _default_email_subject


def test_default_email_subjects_are_chinese() -> None:
    assert _default_email_subject(Path("data/reports/weekly/2026-05-27.md")) == (
        "[AI 技术情报] 周报 - 2026-05-27"
    )
    assert _default_email_subject(Path("data/reports/ecosystem/2026-05-27.md")) == (
        "[AI 生态雷达] 更新 - 2026-05-27"
    )
    assert _default_email_subject(Path("data/reports/alerts/2026-05-27.md")) == (
        "[AI 技术情报提醒] 2026-05-27"
    )


def test_readme_contains_key_chinese_sections() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    for heading in [
        "项目定位",
        "快速开始",
        "隐私边界",
        "GitHub Actions 自动化",
        "License",
    ]:
        assert heading in text
