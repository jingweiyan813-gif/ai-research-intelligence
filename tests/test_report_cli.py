from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from airi.cli import app
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item
from tests.test_scorer import SCORING_CONFIG

runner = CliRunner()


def test_report_weekly_cli_writes_report_file(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        state.save_latest_items(
            [
                make_item(item_id="a", topics=["agents"]).model_dump(mode="json"),
                make_item(item_id="b", topics=["agents"]).model_dump(mode="json"),
            ]
        )
        output = "weekly.md"

        result = runner.invoke(app, ["report", "weekly", "--output", output])

        assert result.exit_code == 0
        assert "Report written:" in result.output
        with open(output, encoding="utf-8") as file:
            text = file.read()
        assert "AI Research Intelligence Weekly Report" in text
        assert "## Top Ranked Items" in text


def test_report_ecosystem_cli_writes_report_file(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        state.save_latest_items([make_item(item_id="a").model_dump(mode="json")])

        result = runner.invoke(app, ["report", "ecosystem", "--output", "eco.md"])

        assert result.exit_code == 0
        with open("eco.md", encoding="utf-8") as file:
            assert "AI Research Ecosystem Report" in file.read()


def test_report_alerts_cli_writes_report_file(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        state.save_latest_items([make_item(item_id="a").model_dump(mode="json")])

        result = runner.invoke(app, ["report", "alerts", "--output", "alerts.md"])

        assert result.exit_code == 0
        with open("alerts.md", encoding="utf-8") as file:
            assert "AI Research Intelligence Alerts" in file.read()


def _fake_app_config() -> SimpleNamespace:
    return SimpleNamespace(
        scoring=SimpleNamespace(
            active_profile="intelligence",
            ranking_profiles=SCORING_CONFIG["ranking_profiles"],
            thresholds=SimpleNamespace(strong_signal=0.70),
            limits=SimpleNamespace(max_report_items=20),
        ),
        profile={"profile": {"interests": ["agents"]}},
    )
