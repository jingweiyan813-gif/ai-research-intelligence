from __future__ import annotations

from typer.testing import CliRunner

from airi.cli import app

runner = CliRunner()


def test_cli_airi_fetch_fake_works() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["fetch", "fake", "--limit", "2", "--no-save"])

    assert result.exit_code == 0
    assert "Total items: 2" in result.output
    assert "Total errors: 0" in result.output
    assert "Source unknown: raw=2, normalized=2, errors=0" in result.output
