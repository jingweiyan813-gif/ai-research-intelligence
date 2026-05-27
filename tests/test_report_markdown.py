from __future__ import annotations

from airi.models import EvidenceRef, SourceType
from airi.report import (
    MarkdownReportRenderer,
    format_evidence_refs,
    format_item_line,
    safe_markdown_text,
)
from tests.factories import make_item


def test_safe_markdown_text_removes_newlines_and_escapes_brackets() -> None:
    assert safe_markdown_text("A [thing]\nnext") == "A \\[thing\\] next"


def test_format_item_line_contains_score_source_title_and_url() -> None:
    item = make_item(title="Test Item")

    line = format_item_line(item, rank=1)

    assert line.startswith("1. 分数=n/a [arxiv/paper]")
    assert "[Test Item](https://example.com/item/1)" in line


def test_format_evidence_refs_contains_ids_and_titles() -> None:
    refs = [
        EvidenceRef(
            item_id="a",
            source=SourceType.ARXIV,
            title="Evidence",
            url="https://example.com/e",
            reason="Representative",
        )
    ]

    text = format_evidence_refs(refs)

    assert "`a`" in text
    assert "Evidence" in text
    assert "Representative" in text


def test_renderer_is_deterministic() -> None:
    renderer = MarkdownReportRenderer()
    sections = [("One", "Body"), ("Two", "More")]

    first = renderer.render_weekly("Title", sections)
    second = renderer.render_weekly("Title", sections)

    assert first == second
    assert first.startswith("# Title")
