from __future__ import annotations

from datetime import datetime, timezone

from airi.intelligence import CrossSourceSignal, PaperRepoLink
from airi.models import IntelligenceItem, ItemType
from airi.report.markdown import MarkdownReportRenderer
from airi.report.weekly import (
    _correlation_section,
    _items_section,
    _link_section,
    _ranked,
)


class EcosystemReportGenerator:
    def __init__(
        self,
        *,
        top: int = 10,
        generated_at: datetime | None = None,
    ) -> None:
        self.top = top
        self.generated_at = generated_at
        self.renderer = MarkdownReportRenderer()

    def generate(
        self,
        items: list[IntelligenceItem],
        correlations: list[CrossSourceSignal],
        paper_repo_links: list[PaperRepoLink],
    ) -> str:
        date = (self.generated_at or datetime.now(timezone.utc)).date().isoformat()
        ranked = _ranked(items)
        return self.renderer.render_ecosystem(
            f"AI Research Ecosystem Report - {date}",
            [
                (
                    "GitHub / DevTools",
                    _items_section(_type(ranked, ItemType.REPO, self.top)),
                ),
                (
                    "Community Signals",
                    _items_section(_type(ranked, ItemType.DISCUSSION, self.top)),
                ),
                (
                    "Company / Lab Updates",
                    _items_section(_type(ranked, ItemType.COMPANY_UPDATE, self.top)),
                ),
                (
                    "Hackathons / Opportunities",
                    _items_section(_type(ranked, ItemType.HACKATHON, self.top)),
                ),
                ("Cross-source Signals", _correlation_section(correlations)),
                ("Paper-Repo Links", _link_section(paper_repo_links)),
            ],
        )


def _type(
    items: list[IntelligenceItem],
    item_type: ItemType,
    limit: int,
) -> list[IntelligenceItem]:
    return [item for item in items if item.item_type == item_type][:limit]
