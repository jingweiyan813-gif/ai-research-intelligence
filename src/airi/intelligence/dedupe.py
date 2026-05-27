from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from airi.models import IntelligenceItem, SourceType
from airi.normalize import (
    canonicalize_arxiv_url,
    canonicalize_github_url,
    get_registered_domain,
    normalize_for_matching,
)


class DuplicateGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    representative_id: str
    duplicate_ids: list[str] = Field(default_factory=list)
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class DedupeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IntelligenceItem]
    duplicate_groups: list[DuplicateGroup] = Field(default_factory=list)
    removed_count: int = Field(ge=0)


class DedupeEngine:
    def dedupe(self, items: list[IntelligenceItem]) -> DedupeResult:
        if not items:
            return DedupeResult(items=[], duplicate_groups=[], removed_count=0)

        parent = {index: index for index in range(len(items))}
        reasons: dict[tuple[int, int], tuple[str, float]] = {}

        for reason, confidence, buckets in self._exact_buckets(items):
            self._union_bucket(parent, reasons, buckets, reason, confidence)
        self._union_near_titles(items, parent, reasons)

        grouped: dict[int, list[int]] = defaultdict(list)
        for index in range(len(items)):
            grouped[self._find(parent, index)].append(index)

        kept_indices: list[int] = []
        duplicate_groups: list[DuplicateGroup] = []
        for indices in grouped.values():
            if len(indices) == 1:
                kept_indices.append(indices[0])
                continue
            representative = self._choose_representative(items, indices)
            duplicate_indices = [index for index in indices if index != representative]
            kept_indices.append(representative)
            reason, confidence = self._best_reason(indices, reasons)
            duplicate_groups.append(
                DuplicateGroup(
                    representative_id=items[representative].id,
                    duplicate_ids=[items[index].id for index in duplicate_indices],
                    reason=reason,
                    confidence=confidence,
                )
            )

        kept_indices.sort()
        return DedupeResult(
            items=[items[index] for index in kept_indices],
            duplicate_groups=duplicate_groups,
            removed_count=sum(len(group.duplicate_ids) for group in duplicate_groups),
        )

    def _exact_buckets(
        self,
        items: list[IntelligenceItem],
    ) -> list[tuple[str, float, dict[str, list[int]]]]:
        id_buckets: dict[str, list[int]] = defaultdict(list)
        url_buckets: dict[str, list[int]] = defaultdict(list)
        fingerprint_buckets: dict[str, list[int]] = defaultdict(list)
        source_buckets: dict[str, list[int]] = defaultdict(list)

        for index, item in enumerate(items):
            id_buckets[item.id].append(index)
            canonical_url = item.canonical_url or item.url
            if canonical_url:
                url_buckets[normalize_for_matching(canonical_url)].append(index)
            if item.content_fingerprint:
                fingerprint_buckets[item.content_fingerprint].append(index)
            source_key = self._source_key(item)
            if source_key:
                source_buckets[source_key].append(index)

        return [
            ("exact id match", 1.0, id_buckets),
            ("canonical url match", 0.98, url_buckets),
            ("content fingerprint match", 0.95, fingerprint_buckets),
            ("source-specific stable key match", 0.97, source_buckets),
        ]

    def _source_key(self, item: IntelligenceItem) -> str | None:
        canonical_url = item.canonical_url or item.url
        if item.source == SourceType.ARXIV:
            return f"arxiv:{canonicalize_arxiv_url(canonical_url)}"
        if item.source == SourceType.GITHUB:
            return f"github:{canonicalize_github_url(canonical_url).lower()}"
        if item.source == SourceType.HACKERNEWS and item.source_metadata.source_item_id:
            return f"hn:{item.source_metadata.source_item_id}"
        if item.source == SourceType.OPENREVIEW:
            key = item.source_metadata.source_item_id or canonical_url
            return f"openreview:{key}"
        if item.source == SourceType.DEVPOST:
            return f"devpost:{normalize_for_matching(canonical_url)}"
        return None

    def _union_near_titles(
        self,
        items: list[IntelligenceItem],
        parent: dict[int, int],
        reasons: dict[tuple[int, int], tuple[str, float]],
    ) -> None:
        token_sets = [self._title_tokens(item.title) for item in items]
        domains = [
            get_registered_domain(item.canonical_url or item.url) for item in items
        ]
        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                if not token_sets[left] or not token_sets[right]:
                    continue
                if len(token_sets[left]) < 3 or len(token_sets[right]) < 3:
                    continue
                same_context = items[left].source == items[right].source or (
                    domains[left] is not None and domains[left] == domains[right]
                )
                if not same_context:
                    continue
                overlap = len(token_sets[left] & token_sets[right]) / max(
                    len(token_sets[left]),
                    len(token_sets[right]),
                )
                if overlap >= 0.9:
                    self._union(parent, reasons, left, right, "near-title match", 0.9)

    def _title_tokens(self, title: str) -> set[str]:
        stopwords = {"a", "an", "the", "and", "or", "for", "with", "to", "of"}
        return {
            token
            for token in normalize_for_matching(title).split()
            if token not in stopwords and len(token) > 1
        }

    def _choose_representative(
        self,
        items: list[IntelligenceItem],
        indices: list[int],
    ) -> int:
        return max(
            indices,
            key=lambda index: self._representative_rank(items[index], -index),
        )

    def _representative_rank(
        self,
        item: IntelligenceItem,
        stable_order: int,
    ) -> tuple[int, int, float, int]:
        has_scores = 1 if item.scores is not None else 0
        signal_count = sum(
            signal is not None
            for signal in (
                item.signals.paper,
                item.signals.github,
                item.signals.community,
                item.signals.hackathon,
                item.signals.company,
            )
        )
        return (has_scores, signal_count, item.fetched_at.timestamp(), stable_order)

    def _best_reason(
        self,
        indices: list[int],
        reasons: dict[tuple[int, int], tuple[str, float]],
    ) -> tuple[str, float]:
        best = ("duplicate match", 0.8)
        index_set = set(indices)
        for (left, right), candidate in reasons.items():
            if left in index_set and right in index_set and candidate[1] > best[1]:
                best = candidate
        return best

    def _union_bucket(
        self,
        parent: dict[int, int],
        reasons: dict[tuple[int, int], tuple[str, float]],
        buckets: dict[str, list[int]],
        reason: str,
        confidence: float,
    ) -> None:
        for indices in buckets.values():
            if len(indices) < 2:
                continue
            first = indices[0]
            for other in indices[1:]:
                self._union(parent, reasons, first, other, reason, confidence)

    def _union(
        self,
        parent: dict[int, int],
        reasons: dict[tuple[int, int], tuple[str, float]],
        left: int,
        right: int,
        reason: str,
        confidence: float,
    ) -> None:
        left_root = self._find(parent, left)
        right_root = self._find(parent, right)
        if left_root != right_root:
            parent[right_root] = left_root
        key = (min(left, right), max(left, right))
        existing = reasons.get(key)
        if existing is None or confidence > existing[1]:
            reasons[key] = (reason, confidence)

    def _find(self, parent: dict[int, int], index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
