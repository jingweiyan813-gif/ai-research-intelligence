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
        title = f"AI 技术情报周报 - {date}"
        return self.renderer.render_weekly(
            title,
            [
                ("执行摘要", _executive_summary(items, claims)),
                ("本周高价值条目", _items_section(ranked[: self.top], ranked=True)),
                (
                    "论文",
                    _items_section(_by_type(ranked, ItemType.PAPER)[: self.top]),
                ),
                (
                    "GitHub / DevTools 项目",
                    _items_section(_by_type(ranked, ItemType.REPO)[: self.top]),
                ),
                (
                    "公司 / 实验室动态",
                    _items_section(
                        _by_type(ranked, ItemType.COMPANY_UPDATE)[: self.top]
                    ),
                ),
                (
                    "社区信号",
                    _items_section(_by_type(ranked, ItemType.DISCUSSION)[: self.top]),
                ),
                (
                    "黑客松 / 机会",
                    _items_section(_by_type(ranked, ItemType.HACKATHON)[: self.top]),
                ),
                ("新兴趋势", _trend_section(claims)),
                ("跨源信号", _correlation_section(correlations)),
                ("Paper-Repo 关联", _link_section(paper_repo_links)),
                ("建议行动", _actions_section(ranked, claims)),
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
            f"- 条目总数: {len(items)}",
            f"- 高频主题: {_counter_summary(topics)}",
            f"- 主要来源: {_counter_summary(sources)}",
            "- 最强趋势: "
            + (", ".join(claim.topic for claim in strongest) if strongest else "暂无"),
        ]
    )


def _counter_summary(counter: Counter[str]) -> str:
    if not counter:
        return "暂无"
    return ", ".join(f"{key} ({count})" for key, count in counter.most_common(5))


def _items_section(items: list[IntelligenceItem], *, ranked: bool = False) -> str:
    if not items:
        return "暂无条目。"
    lines = []
    for index, item in enumerate(items, start=1):
        line = format_item_line(item, index if ranked else None)
        reason = _top_reason(item)
        if reason:
            line += f" — 原因：{safe_markdown_text(reason)}"
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
        return "暂无新兴趋势。"
    blocks = []
    for claim in sorted(claims, key=lambda item: (-item.confidence, item.topic)):
        blocks.append(
            f"- {safe_markdown_text(claim.claim)} "
            f"(置信度={claim.confidence:.2f})\n"
            f"  证据：\n{_indent(format_evidence_refs(claim.evidence_refs), 2)}"
        )
    return "\n".join(blocks)


def _correlation_section(signals: list[CrossSourceSignal]) -> str:
    if not signals:
        return "暂无跨源信号。"
    lines = []
    for signal in sorted(signals, key=lambda item: (-item.strength, item.topic)):
        lines.append(
            f"- {safe_markdown_text(signal.topic)}: 强度={signal.strength:.2f}; "
            f"来源={', '.join(signal.sources)}; 条目数={len(signal.item_ids)}"
        )
    return "\n".join(lines)


def _link_section(links: list[PaperRepoLink]) -> str:
    if not links:
        return "暂无 Paper-Repo 关联。"
    lines = []
    for link in links:
        terms = ", ".join(link.matched_terms) if link.matched_terms else "暂无"
        lines.append(
            f"- `{link.paper_item_id}` -> `{link.repo_item_id}` "
            f"置信度={link.confidence:.2f}; "
            f"原因={safe_markdown_text(link.reason)}; "
            f"匹配={safe_markdown_text(terms)}"
        )
    return "\n".join(lines)


def _actions_section(items: list[IntelligenceItem], claims: list[TrendClaim]) -> str:
    papers = _by_type(items, ItemType.PAPER)
    repos = _by_type(items, ItemType.REPO)
    hackathons = _by_type(items, ItemType.HACKATHON)
    actions = []
    if papers:
        actions.append(f"- 阅读高价值论文: {safe_markdown_text(papers[0].title)}")
    if repos:
        actions.append(f"- 试用高价值 repo: {safe_markdown_text(repos[0].title)}")
    if claims:
        actions.append(f"- 关注趋势: {safe_markdown_text(claims[0].topic)}")
    if hackathons:
        actions.append(
            f"- 收藏黑客松: {safe_markdown_text(hackathons[0].title)}"
        )
    return "\n".join(actions) if actions else "- 暂无建议行动。"


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())
