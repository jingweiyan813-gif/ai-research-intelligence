from __future__ import annotations

import subprocess
import sys
from email import policy
from email.parser import Parser
from pathlib import Path

from airi.delivery import preview_without_credentials
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item


def test_run_weekly_dry_run_supports_no_email() -> None:
    with _isolated_state():
        result = subprocess.run(
            [sys.executable, "scripts/run_weekly.py", "--dry-run", "--no-email"],
            check=False,
            capture_output=True,
            text=True,
        )
        reports = sorted(Path("data/reports/weekly").glob("*.md"))
        assert reports
        report_text = reports[-1].read_text(encoding="utf-8")
        preview = preview_without_credentials(
            "[AI 技术情报] 周报 - 2026-05-27",
            report_text,
            Path("data/reports/email_preview"),
        )
        message = Parser(policy=policy.default).parsestr(
            preview.read_text(encoding="utf-8")
        )

    assert result.returncode == 0
    assert "Weekly report:" in result.stdout
    assert "super-secret" not in result.stdout
    for heading in [
        "AI 技术情报周报",
        "执行摘要",
        "本周高价值条目",
        "论文",
        "GitHub / DevTools 项目",
        "公司 / 实验室动态",
        "社区信号",
        "黑客松 / 机会",
        "新兴趋势",
        "跨源信号",
        "Paper-Repo 关联",
        "建议行动",
    ]:
        assert heading in report_text
    for english_scaffold in [
        "Executive Summary",
        "Top Ranked Items",
        "Recommended Actions",
    ]:
        assert english_scaffold not in report_text
    assert message["Subject"] == "[AI 技术情报] 周报 - 2026-05-27"
    assert "AI 技术情报周报" in message.get_content()


def test_run_eval_script() -> None:
    with _isolated_state():
        result = subprocess.run(
            [sys.executable, "scripts/run_eval.py"],
            check=False,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0
    assert "Eval report:" in result.stdout


class _isolated_state:
    def __enter__(self):  # type: ignore[no-untyped-def]
        self._cwd = __import__("os").getcwd()
        self._tmp = __import__("tempfile").TemporaryDirectory()
        __import__("shutil").copytree(
            self._cwd,
            self._tmp.name,
            dirs_exist_ok=True,
            ignore=__import__("shutil").ignore_patterns(
                ".git",
                ".venv",
                "__pycache__",
                "*.pyc",
            ),
        )
        __import__("os").chdir(self._tmp.name)
        state = StateStore(StoragePaths.default())
        state.save_latest_items([make_item(item_id="a").model_dump(mode="json")])
        return self

    def __exit__(self, *args):  # type: ignore[no-untyped-def]
        __import__("os").chdir(self._cwd)
        self._tmp.cleanup()
