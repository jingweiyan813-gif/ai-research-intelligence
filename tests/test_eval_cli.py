from __future__ import annotations

from typer.testing import CliRunner

from airi.cli import app
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item

runner = CliRunner()


def test_cli_eval_ranking_writes_report(isolated_cwd) -> None:  # type: ignore[no-untyped-def]
    state = StateStore(StoragePaths.default())
    state.save_latest_items([make_item(item_id="a").model_dump(mode="json")])
    gold = "gold.yml"
    with open(gold, "w", encoding="utf-8") as file:
        file.write("relevant_item_ids:\n  - a\n")

    result = runner.invoke(
        app,
        ["eval", "ranking", "--gold", gold, "--output", "eval.md"],
    )

    assert result.exit_code == 0
    assert "precision_at_5" in result.output
    with open("eval.md", encoding="utf-8") as file:
        assert "AI Research Intelligence Eval Report" in file.read()
