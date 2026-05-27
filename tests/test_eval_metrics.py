from __future__ import annotations

from airi.eval import (
    duplicate_rate,
    evidence_coverage_for_report,
    negative_filter_presence,
    precision_at_k,
)
from tests.factories import make_item


def test_precision_at_k_computes_expected_value() -> None:
    items = [make_item(item_id="a"), make_item(item_id="b")]
    labels = {"relevant_item_ids": ["a"]}

    assert precision_at_k(items, labels, 2) == 0.5


def test_duplicate_rate_detects_duplicate_canonical_urls() -> None:
    items = [
        make_item(item_id="a", canonical_url="https://x.test/a"),
        make_item(item_id="b", canonical_url="https://x.test/a"),
    ]

    assert duplicate_rate(items) == 0.5


def test_evidence_coverage_for_report() -> None:
    report = "- Claim confidence=0.80\n  Evidence:\n  - `item_a` Title"

    assert evidence_coverage_for_report(report) == 1.0


def test_negative_filter_presence() -> None:
    items = [make_item(title="Useful paper"), make_item(title="Unrelated spam")]

    assert negative_filter_presence(items) == 0.5
