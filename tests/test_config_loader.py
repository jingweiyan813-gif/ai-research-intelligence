from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from airi.cli import app
from airi.config.loader import load_app_config

runner = CliRunner()


def copy_default_configs(tmp_path: Path) -> Path:
    target = tmp_path / "configs"
    shutil.copytree("configs", target, ignore=shutil.ignore_patterns("*.local.yml"))
    return target


def test_default_configs_load_successfully() -> None:
    config = load_app_config()

    assert config.sources.sources
    assert config.topics.primary_topics
    assert config.scoring.weights.topic_relevance > 0


def test_optional_local_files_are_missing_gracefully(tmp_path: Path) -> None:
    config_dir = copy_default_configs(tmp_path)
    config = load_app_config(config_dir)

    assert config.local_overrides == {
        "profile": False,
        "email": False,
        "watchlists": False,
    }


def test_config_show_output_does_not_include_secrets() -> None:
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "password" not in result.output.lower()
    assert "api_key" not in result.output.lower()
    assert "replace-me" not in result.output
    assert "not-set" not in result.output
    assert "enabled_sources" in result.output
