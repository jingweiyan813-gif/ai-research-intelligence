from __future__ import annotations

from typer.testing import CliRunner

from airi.cli import app
from airi.connectors import FakeConnector

runner = CliRunner()


def test_cli_airi_fetch_hn_works_with_mocked_connector(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import airi.cli as cli_module

    monkeypatch.setattr(
        cli_module,
        "HackerNewsConnector",
        lambda _config: FakeConnector(item_count=2),
    )
    result = runner.invoke(app, ["fetch", "hn", "--limit", "2", "--no-save"])

    assert result.exit_code == 0
    assert "Total items: 2" in result.output
    assert "Total errors: 0" in result.output
