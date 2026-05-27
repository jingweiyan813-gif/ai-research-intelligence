from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from airi.cli import app
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item

runner = CliRunner()


def test_cli_airi_rank_works_on_latest_items(monkeypatch, isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [make_item(item_id="a", topics=["ai_agents"]).model_dump(mode="json")]
    )

    result = runner.invoke(app, ["rank", "--top", "10"])

    assert result.exit_code == 0
    assert "AI Agent Paper" in result.output
    saved = state.load_latest_items()[0]
    assert saved["scores"]["final_score"] >= 0


def test_cli_airi_rank_explain_works(monkeypatch, isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [make_item(item_id="a", topics=["ai_agents"]).model_dump(mode="json")]
    )
    runner.invoke(app, ["rank"])

    result = runner.invoke(app, ["rank", "explain", "a"])

    assert result.exit_code == 0
    assert "最终分数" in result.output
    assert "根据当前排序策略的配置权重加权计算" in result.output
    assert "Weighted sum from configured scoring weights" not in result.output


def test_cli_airi_rank_profile_override_works(monkeypatch, isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [make_item(item_id="a", topics=["ai_agents"]).model_dump(mode="json")]
    )

    result = runner.invoke(
        app,
        ["rank", "--profile", "item_baseline", "--top", "5"],
    )

    assert result.exit_code == 0
    assert "AI Agent Paper" in result.output


def test_cli_airi_rank_invalid_profile_fails(monkeypatch, isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [make_item(item_id="a", topics=["ai_agents"]).model_dump(mode="json")]
    )

    result = runner.invoke(app, ["rank", "--profile", "missing"])

    assert result.exit_code == 1
    assert "Unknown ranking profile" in result.output


def _fake_app_config() -> SimpleNamespace:
    return SimpleNamespace(
        scoring=SimpleNamespace(
            active_profile="intelligence",
            ranking_profiles={
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
            limits=SimpleNamespace(max_report_items=20),
        ),
        profile={"profile": {"interests": ["ai_agents"]}},
    )
