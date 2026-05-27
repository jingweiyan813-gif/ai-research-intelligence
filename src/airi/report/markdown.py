from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from airi.models import EvidenceRef, IntelligenceItem


class MarkdownReportRenderer:
    def render_weekly(
        self,
        title: str,
        sections: Iterable[tuple[str, str]],
    ) -> str:
        return _render(title, sections)

    def render_ecosystem(
        self,
        title: str,
        sections: Iterable[tuple[str, str]],
    ) -> str:
        return _render(title, sections)

    def render_alerts(
        self,
        title: str,
        sections: Iterable[tuple[str, str]],
    ) -> str:
        return _render(title, sections)


def format_item_line(item: IntelligenceItem, rank: int | None = None) -> str:
    prefix = f"{rank}. " if rank is not None else "- "
    label = f"[{item.source.value}/{item.item_type.value}]"
    return (
        f"{prefix}{format_score(item)} {label} "
        f"[{safe_markdown_text(item.title)}]({item.url})"
    )


def format_score(item: IntelligenceItem) -> str:
    if item.scores is None:
        return "分数=n/a"
    return f"分数={item.scores.final_score:.3f}"


def format_evidence_refs(refs: Iterable[EvidenceRef]) -> str:
    lines = []
    for ref in refs:
        reason = f" — {safe_markdown_text(ref.reason)}" if ref.reason else ""
        lines.append(
            f"- `{ref.item_id}` [{safe_markdown_text(ref.title)}]({ref.url}){reason}"
        )
    return "\n".join(lines) if lines else "- 暂无证据引用。"


def safe_markdown_text(text: Any) -> str:
    value = "" if text is None else str(text)
    replacements = {
        "\r": " ",
        "\n": " ",
        "|": "\\|",
        "[": "\\[",
        "]": "\\]",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return " ".join(value.split())


def _render(title: str, sections: Iterable[tuple[str, str]]) -> str:
    parts = [f"# {safe_markdown_text(title)}"]
    for heading, body in sections:
        cleaned = body.strip() or "暂无内容。"
        parts.append(f"## {safe_markdown_text(heading)}\n{cleaned}")
    return "\n\n".join(parts).rstrip() + "\n"
