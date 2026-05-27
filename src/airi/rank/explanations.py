from __future__ import annotations

from airi.models import IntelligenceItem


def explain_score(item: IntelligenceItem) -> str:
    if item.scores is None:
        return f"{item.id}: 暂无评分"
    lines = [f"{item.title}", f"最终分数: {item.scores.final_score:.3f}"]
    for breakdown in item.scores.breakdowns:
        lines.append(
            f"- {breakdown.dimension}: {breakdown.score:.3f} — {breakdown.reason}"
        )
    return "\n".join(lines)


def summarize_top_items(items: list[IntelligenceItem], top: int = 10) -> str:
    lines = []
    for rank, item in enumerate(items[:top], start=1):
        final_score = item.scores.final_score if item.scores is not None else 0.0
        label = f"[{item.source.value}/{item.item_type.value}]"
        lines.append(f"{rank}. {final_score:.3f} {label} {item.title}")
    return "\n".join(lines)
