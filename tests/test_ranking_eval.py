from __future__ import annotations

from airi.eval import RankingEvaluator
from tests.factories import make_item


def test_eval_report_renders(tmp_path) -> None:  # type: ignore[no-untyped-def]
    gold = tmp_path / "gold.yml"
    gold.write_text("relevant_item_ids:\n  - a\n", encoding="utf-8")
    evaluator = RankingEvaluator(gold)

    metrics, report = evaluator.evaluate_and_render([make_item(item_id="a")])

    assert metrics["precision_at_5"] == 1.0
    assert "# AI Research Intelligence Eval Report" in report
    assert "precision_at_5" in report
