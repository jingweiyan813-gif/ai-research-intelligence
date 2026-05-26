from __future__ import annotations

from typer.testing import CliRunner

from airi.cli import app
from airi.connectors import FakeConnector

runner = CliRunner()


def test_cli_airi_fetch_github_works_with_mocked_connector(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(
        cli_module,
        "GitHubConnector",
        lambda _config: FakeConnector(item_count=2),
    )
    result = runner.invoke(app, ["fetch", "github", "--limit", "2", "--no-save"])

    assert result.exit_code == 0
    assert "Total items: 2" in result.output
    assert "Total errors: 0" in result.output
    assert "Source unknown: raw=2, normalized=2, errors=0" in result.output
