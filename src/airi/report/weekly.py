from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from airi.intelligence import CrossSourceSignal, PaperRepoLink
from airi.models import IntelligenceItem, ItemType, TrendClaim
from airi.report.markdown import (
    MarkdownReportRenderer,
    format_evidence_refs,
    format_item_line,
    safe_markdown_text,
)


class WeeklyReportGenerator:
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
        trends: Any,
        correlations: list[CrossSourceSignal],
        paper_repo_links: list[PaperRepoLink],
    ) -> str:
        ranked = _ranked(items)
        claims = _trend_claims(trends)
        date = (self.generated_at or datetime.now(timezone.utc)).date().isoformat()
        title = f"AI Research Intelligence Weekly Report - {date}"
        return self.renderer.render_weekly(
            title,
            [
                ("Executive Summary", _executive_summary(items, claims)),
                ("Top Ranked Items", _items_section(ranked[: self.top], ranked=True)),
                (
                    "Papers",
                    _items_section(_by_type(ranked, ItemType.PAPER)[: self.top]),
                ),
                (
                    "GitHub / DevTools",
                    _items_section(_by_type(ranked, ItemType.REPO)[: self.top]),
                ),
                (
                    "Company / Lab Updates",
                    _items_section(
                        _by_type(ranked, ItemType.COMPANY_UPDATE)[: self.top]
                    ),
                ),
                (
                    "Community Signals",
                    _items_section(_by_type(ranked, ItemType.DISCUSSION)[: self.top]),
                ),
                (
                    "Hackathons / Opportunities",
                    _items_section(_by_type(ranked, ItemType.HACKATHON)[: self.top]),
                ),
                ("Emerging Trends", _trend_section(claims)),
                ("Cross-source Signals", _correlation_section(correlations)),
                ("Paper-Repo Links", _link_section(paper_repo_links)),
                ("Recommended Actions", _actions_section(ranked, claims)),
            ],
        )


def _ranked(items: list[IntelligenceItem]) -> list[IntelligenceItem]:
    return sorted(
        items,
        key=lambda item: (
            -(item.scores.final_score if item.scores is not None else 0.0),
            item.title,
            item.id,
        ),
    )


def _by_type(
    items: list[IntelligenceItem],
    item_type: ItemType,
) -> list[IntelligenceItem]:
    return [item for item in items if item.item_type == item_type]


def _trend_claims(trends: Any) -> list[TrendClaim]:
    if trends is None:
        return []
    claims = getattr(trends, "claims", trends)
    if isinstance(claims, list):
        return claims
    return []


def _executive_summary(
    items: list[IntelligenceItem],
    claims: list[TrendClaim],
) -> str:
    topics = Counter(topic for item in items for topic in item.topics)
    sources = Counter(item.source.value for item in items)
    strongest = sorted(
        claims,
        key=lambda claim: (-claim.confidence, claim.topic, claim.id),
    )[:3]
    return "\n".join(
        [
            f"- Total items: {len(items)}",
            f"- Top topics: {_counter_summary(topics)}",
            f"- Top sources: {_counter_summary(sources)}",
            "- Strongest trends: "
            + (", ".join(claim.topic for claim in strongest) if strongest else "none"),
        ]
    )


def _counter_summary(counter: Counter[str]) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key} ({count})" for key, count in counter.most_common(5))


def _items_section(items: list[IntelligenceItem], *, ranked: bool = False) -> str:
    if not items:
        return "No items."
    lines = []
    for index, item in enumerate(items, start=1):
        line = format_item_line(item, index if ranked else None)
        reason = _top_reason(item)
        if reason:
            line += f" — why: {safe_markdown_text(reason)}"
        lines.append(line)
    return "\n".join(lines)


def _top_reason(item: IntelligenceItem) -> str | None:
    if item.scores is None:
        return None
    candidates = [
        breakdown
        for breakdown in item.scores.breakdowns
        if breakdown.dimension != "final_score"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda breakdown: breakdown.score).reason


def _trend_section(claims: list[TrendClaim]) -> str:
    if not claims:
        return "No emerging trends."
    blocks = []
    for claim in sorted(claims, key=lambda item: (-item.confidence, item.topic)):
        blocks.append(
            f"- {safe_markdown_text(claim.claim)} "
            f"(confidence={claim.confidence:.2f})\n"
            f"  Evidence:\n{_indent(format_evidence_refs(claim.evidence_refs), 2)}"
        )
    return "\n".join(blocks)


def _correlation_section(signals: list[CrossSourceSignal]) -> str:
    if not signals:
        return "No cross-source signals."
    lines = []
    for signal in sorted(signals, key=lambda item: (-item.strength, item.topic)):
        lines.append(
            f"- {safe_markdown_text(signal.topic)}: strength={signal.strength:.2f}; "
            f"sources={', '.join(signal.sources)}; items={len(signal.item_ids)}"
        )
    return "\n".join(lines)


def _link_section(links: list[PaperRepoLink]) -> str:
    if not links:
        return "No paper-repo links."
    lines = []
    for link in links:
        terms = ", ".join(link.matched_terms) if link.matched_terms else "none"
        lines.append(
            f"- `{link.paper_item_id}` -> `{link.repo_item_id}` "
            f"confidence={link.confidence:.2f}; "
            f"reason={safe_markdown_text(link.reason)}; "
            f"matched={safe_markdown_text(terms)}"
        )
    return "\n".join(lines)


def _actions_section(items: list[IntelligenceItem], claims: list[TrendClaim]) -> str:
    papers = _by_type(items, ItemType.PAPER)
    repos = _by_type(items, ItemType.REPO)
    hackathons = _by_type(items, ItemType.HACKATHON)
    actions = []
    if papers:
        actions.append(f"- Read top paper: {safe_markdown_text(papers[0].title)}")
    if repos:
        actions.append(f"- Try top repo: {safe_markdown_text(repos[0].title)}")
    if claims:
        actions.append(f"- Watch trend: {safe_markdown_text(claims[0].topic)}")
    if hackathons:
        actions.append(
            f"- Bookmark hackathon: {safe_markdown_text(hackathons[0].title)}"
        )
    return "\n".join(actions) if actions else "- No recommended actions."


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())
