from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airi.intelligence import CrossSourceSignal
from airi.models import IntelligenceItem, ItemType
from airi.report.markdown import (
    MarkdownReportRenderer,
    format_item_line,
    safe_markdown_text,
)


class AlertsReportGenerator:
    def __init__(
        self,
        *,
        alert_threshold: float = 0.7,
        generated_at: datetime | None = None,
        deadline_days: int = 14,
    ) -> None:
        self.alert_threshold = alert_threshold
        self.generated_at = generated_at or datetime.now(timezone.utc)
        self.deadline_days = deadline_days
        self.renderer = MarkdownReportRenderer()

    def generate(
        self,
        items: list[IntelligenceItem],
        correlations: list[CrossSourceSignal],
    ) -> str:
        date = self.generated_at.date().isoformat()
        body = self._alerts_body(items, correlations)
        return self.renderer.render_alerts(
            f"AI 技术情报提醒 - {date}",
            [("提醒", body)],
        )

    def _alerts_body(
        self,
        items: list[IntelligenceItem],
        correlations: list[CrossSourceSignal],
    ) -> str:
        sections = []
        high_score = [
            item
            for item in items
            if item.scores is not None
            and item.scores.final_score >= self.alert_threshold
        ]
        if high_score:
            lines = ["### 高分条目"]
            lines.extend(format_item_line(item) for item in _rank(high_score))
            sections.append("\n".join(lines))

        strong_signals = [
            signal for signal in correlations if signal.strength >= self.alert_threshold
        ]
        if strong_signals:
            lines = ["### 强跨源信号"]
            for signal in sorted(
                strong_signals,
                key=lambda item: (-item.strength, item.topic),
            ):
                sources = ", ".join(signal.sources)
                lines.append(
                    f"- {safe_markdown_text(signal.topic)} "
                    f"强度={signal.strength:.2f}; 来源={sources}"
                )
            sections.append("\n".join(lines))

        deadline_items = [item for item in items if self._deadline_soon(item)]
        if deadline_items:
            lines = ["### 即将截止的黑客松"]
            lines.extend(format_item_line(item) for item in _rank(deadline_items))
            sections.append("\n".join(lines))

        return "\n\n".join(sections) if sections else "暂无高信号提醒。"

    def _deadline_soon(self, item: IntelligenceItem) -> bool:
        if item.item_type != ItemType.HACKATHON or item.signals.hackathon is None:
            return False
        deadline = item.signals.hackathon.deadline_at
        if deadline is None:
            return False
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        upper = self.generated_at + timedelta(days=self.deadline_days)
        return self.generated_at <= deadline <= upper


def _rank(items: list[IntelligenceItem]) -> list[IntelligenceItem]:
    return sorted(
        items,
        key=lambda item: (
            -(item.scores.final_score if item.scores is not None else 0.0),
            item.title,
            item.id,
        ),
    )
