from __future__ import annotations

import re
from collections import Counter
from typing import Any

from airi.models import IntelligenceItem
from airi.normalize import normalize_for_matching


def precision_at_k(
    items: list[IntelligenceItem],
    gold_labels: dict[str, Any],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant = set(gold_labels.get("relevant_item_ids", []))
    if not relevant:
        return 0.0
    top_items = items[:k]
    hits = sum(item.id in relevant for item in top_items)
    return hits / min(k, len(top_items) or k)


def duplicate_rate(items: list[IntelligenceItem]) -> float:
    if not items:
        return 0.0
    keys = [item.canonical_url or item.content_fingerprint or item.id for item in items]
    counts = Counter(keys)
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    return duplicates / len(items)


def evidence_coverage_for_report(markdown_text: str) -> float:
    claims = len(re.findall(r"(?im)^- .*confidence=", markdown_text))
    if claims == 0:
        return 1.0
    evidence_mentions = len(re.findall(r"`[^`]+`", markdown_text))
    return min(1.0, evidence_mentions / claims)


def negative_filter_presence(items: list[IntelligenceItem]) -> float:
    if not items:
        return 0.0
    negative_terms = {"unrelated", "spam", "crypto", "casino"}
    flagged = 0
    for item in items:
        text = normalize_for_matching(
            " ".join([item.title, item.abstract or "", " ".join(item.keywords)])
        )
        if any(term in text for term in negative_terms):
            flagged += 1
    return flagged / len(items)
