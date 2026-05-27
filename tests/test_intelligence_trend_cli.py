from __future__ import annotations

from datetime import datetime, timezone

from typer.testing import CliRunner

from airi.cli import app
from airi.models import ItemType, SourceType
from airi.rank import ItemScorer
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item
from tests.test_scorer import SCORING_CONFIG

runner = CliRunner()


def test_airi_trends_works_on_latest_items(isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [
            make_item(
                item_id="a",
                topics=["ai_agents"],
                fetched_at=datetime.now(timezone.utc),
            ).model_dump(mode="json"),
            make_item(
                item_id="b",
                topics=["ai_agents"],
                fetched_at=datetime.now(timezone.utc),
            ).model_dump(mode="json"),
        ]
    )

    result = runner.invoke(app, ["trends"])

    assert result.exit_code == 0
    assert "ai_agents" in result.output


def test_airi_trends_update_timeseries_works(isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [make_item(item_id="a", topics=["ai_agents"]).model_dump(mode="json")]
    )

    result = runner.invoke(app, ["trends", "--update-timeseries"])

    assert result.exit_code == 0
    assert state.load_topic_timeseries()


def test_airi_correlate_works(isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [
            make_item(item_id="a", topics=["ai_agents"]).model_dump(mode="json"),
            make_item(
                item_id="b",
                topics=["coding_agents"],
            ).model_dump(mode="json"),
        ]
    )

    result = runner.invoke(app, ["correlate"])

    assert result.exit_code == 0
    assert "Cross-source signals" in result.output


def test_airi_correlate_apply_works(monkeypatch, isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    state = StateStore(StoragePaths.default())
    scorer = ItemScorer(SCORING_CONFIG)
    item = make_item(item_id="a", topics=["ai_agents"])
    state.save_latest_items(
        [item.model_copy(update={"scores": scorer.score(item)}).model_dump(mode="json")]
    )

    result = runner.invoke(app, ["correlate", "--apply"])

    assert result.exit_code == 0
    saved = state.load_latest_items()[0]
    assert saved["scores"]["cross_source_correlation"] == 0.1


def test_airi_link_paper_repos_works(isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default())
    state.save_latest_items(
        [
            make_item(
                item_id="paper",
                abstract="See openai/codeagent for implementation.",
            ).model_dump(mode="json"),
            make_item(
                item_id="repo",
                title="openai/codeagent",
                source=SourceType.GITHUB,
                item_type=ItemType.REPO,
                repos=["openai/codeagent"],
            ).model_dump(mode="json"),
        ]
    )

    result = runner.invoke(app, ["link", "paper-repos"])

    assert result.exit_code == 0
    assert "paper -> repo" in result.output


def _fake_app_config() -> object:
    from types import SimpleNamespace

    return SimpleNamespace(scoring=SCORING_CONFIG)
