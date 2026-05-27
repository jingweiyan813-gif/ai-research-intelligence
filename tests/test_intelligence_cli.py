from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from airi.cli import app
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item

runner = CliRunner()


def test_intelligence_dedupe_works_on_latest_items() -> None:
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        items = [
            make_item(item_id="a", canonical_url="https://example.com/a"),
            make_item(item_id="b", canonical_url="https://example.com/a"),
        ]
        state.save_latest_items(item.model_dump(mode="json") for item in items)

        result = runner.invoke(app, ["intelligence", "dedupe"])

        assert result.exit_code == 0
        assert "Removed duplicates: 1" in result.output
        assert len(state.load_latest_items()) == 1


def test_intelligence_novelty_works_on_latest_items() -> None:
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        item = make_item(item_id="new")
        state.save_latest_items([item.model_dump(mode="json")])

        result = runner.invoke(app, ["intelligence", "novelty"])

        assert result.exit_code == 0
        assert "Items checked: 1" in result.output
        assert "New items: 1" in result.output
        assert state.load_seen_items() == {}


def test_intelligence_novelty_update_seen() -> None:
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        item = make_item(item_id="new")
        state.save_latest_items([item.model_dump(mode="json")])

        result = runner.invoke(app, ["intelligence", "novelty", "--update-seen"])

        assert result.exit_code == 0
        assert state.load_seen_items()["new"]["seen_count"] == 1


def test_intelligence_extract_works_on_latest_items(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        item = make_item(title="OpenAI AI agent for code", keywords=["code"])
        state.save_latest_items([item.model_dump(mode="json")])

        result = runner.invoke(app, ["intelligence", "extract"])

        assert result.exit_code == 0
        assert "Items processed: 1" in result.output
        saved = state.load_latest_items()[0]
        assert "ai_agents" in saved["topics"]
        assert "OpenAI" in saved["entities"]


def test_intelligence_extract_no_save_does_not_write(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(cli_module, "load_app_config", _fake_app_config)
    with runner.isolated_filesystem():
        state = StateStore(StoragePaths.default())
        item = make_item(title="OpenAI AI agent")
        state.save_latest_items([item.model_dump(mode="json")])

        result = runner.invoke(app, ["intelligence", "extract", "--no-save"])

        assert result.exit_code == 0
        saved = state.load_latest_items()[0]
        assert saved["topics"] == []


def _fake_app_config() -> SimpleNamespace:
    return SimpleNamespace(
        topics={
            "primary_topics": [
                {"id": "ai_agents", "keywords": ["AI agent", "agent"]},
                {"id": "coding_agents", "keywords": ["code"]},
            ],
            "negative_topics": [],
        },
        watchlists={"watchlists": []},
    )
