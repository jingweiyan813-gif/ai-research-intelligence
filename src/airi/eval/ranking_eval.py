from __future__ import annotations

from pathlib import Path

from airi.eval.dataset import DEFAULT_GOLD_PATH, load_gold_items
from airi.eval.metrics import (
    duplicate_rate,
    evidence_coverage_for_report,
    negative_filter_presence,
    precision_at_k,
)
from airi.models import IntelligenceItem


class RankingEvaluator:
    def __init__(self, gold_path: Path = DEFAULT_GOLD_PATH) -> None:
        self.gold_path = gold_path

    def evaluate(
        self,
        items: list[IntelligenceItem],
        report_markdown: str = "",
    ) -> dict[str, float]:
        gold = load_gold_items(self.gold_path)
        return {
            "precision_at_5": precision_at_k(items, gold, 5),
            "precision_at_10": precision_at_k(items, gold, 10),
            "duplicate_rate": duplicate_rate(items),
            "evidence_coverage": evidence_coverage_for_report(report_markdown),
            "negative_filter_presence": negative_filter_presence(items),
        }

    def render_markdown(self, metrics: dict[str, float]) -> str:
        lines = ["# AI Research Intelligence Eval Report", "", "## Metrics"]
        for key in sorted(metrics):
            lines.append(f"- {key}: {metrics[key]:.3f}")
        lines.append("")
        lines.append(f"Gold file: `{self.gold_path}`")
        return "\n".join(lines).rstrip() + "\n"

    def evaluate_and_render(
        self,
        items: list[IntelligenceItem],
        report_markdown: str = "",
    ) -> tuple[dict[str, float], str]:
        metrics = self.evaluate(items, report_markdown)
        return metrics, self.render_markdown(metrics)
