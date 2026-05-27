from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict

from airi.models import (
    EvidenceRef,
    IntelligenceItem,
    ItemType,
    SourceType,
    TopicTrend,
    TrendClaim,
    TrendType,
)
from airi.storage import StateStore


class TrendAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trends: list[TopicTrend]
    claims: list[TrendClaim]
    analyzed_item_count: int
    window_start: datetime
    window_end: datetime


class TrendEngine:
    def __init__(self, state_store: StateStore) -> None:
        self.state_store = state_store

    def analyze(
        self,
        items: list[IntelligenceItem],
        window_days: int = 30,
    ) -> TrendAnalysisResult:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=window_days)
        window_items = [
            item for item in items if _item_time(item) >= window_start and item.topics
        ]
        previous_counts = self._previous_window_counts(window_start, window_days)
        grouped: dict[str, list[IntelligenceItem]] = defaultdict(list)
        for item in window_items:
            for topic in item.topics:
                grouped[topic].append(item)

        trends = [
            self._build_trend(
                topic,
                topic_items,
                previous_counts.get(topic, 0),
                window_start,
                window_end,
            )
            for topic, topic_items in sorted(grouped.items())
        ]
        claims = [
            self._build_claim(trend, grouped[trend.topic], window_start, window_end)
            for trend in trends
            if trend.trend_type != TrendType.NOISE
        ]
        return TrendAnalysisResult(
            trends=trends,
            claims=claims,
            analyzed_item_count=len(window_items),
            window_start=window_start,
            window_end=window_end,
        )

    def update_timeseries(
        self,
        items: list[IntelligenceItem],
        as_of: datetime | None = None,
    ) -> None:
        date_key = (as_of or datetime.now(timezone.utc)).date().isoformat()
        timeseries = self.state_store.load_topic_timeseries()
        day_counts = _topic_counts(items)
        timeseries[date_key] = {
            topic: {
                "item_count": counts["item_count"],
                "paper_count": counts["paper_count"],
                "repo_count": counts["repo_count"],
                "hn_count": counts["hn_count"],
                "company_count": counts["company_count"],
                "source_count": len(counts["sources"]),
            }
            for topic, counts in sorted(day_counts.items())
        }
        self.state_store.save_topic_timeseries(timeseries)

    def _previous_window_counts(
        self,
        window_start: datetime,
        window_days: int,
    ) -> dict[str, int]:
        previous_start = window_start - timedelta(days=window_days)
        counts: dict[str, int] = defaultdict(int)
        for date_key, topics in self.state_store.load_topic_timeseries().items():
            try:
                day = datetime.fromisoformat(date_key).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if not previous_start <= day < window_start or not isinstance(topics, dict):
                continue
            for topic, metrics in topics.items():
                if isinstance(metrics, dict):
                    counts[str(topic)] += int(metrics.get("item_count", 0))
        return dict(counts)

    def _build_trend(
        self,
        topic: str,
        items: list[IntelligenceItem],
        previous_count: int,
        window_start: datetime,
        window_end: datetime,
    ) -> TopicTrend:
        counts = _counts_for_items(items)
        current_count = counts["item_count"]
        source_count = len(counts["sources"])
        growth_rate = (current_count - previous_count) / max(previous_count, 1)
        momentum_score = _bounded_momentum(growth_rate, source_count, current_count)
        novelty_score = _average_novelty(items)
        trend_type = _classify_trend(
            current_count,
            previous_count,
            growth_rate,
            source_count,
        )
        representatives = _representative_items(items)
        return TopicTrend(
            topic=topic,
            window_start=window_start,
            window_end=window_end,
            item_count=current_count,
            source_count=source_count,
            paper_count=counts["paper_count"],
            repo_count=counts["repo_count"],
            hn_count=counts["hn_count"],
            company_count=counts["company_count"],
            previous_window_count=previous_count,
            growth_rate=growth_rate,
            momentum_score=momentum_score,
            novelty_score=novelty_score,
            trend_type=trend_type,
            representative_item_ids=[item.id for item in representatives],
            interpretation=(
                f"{topic} has {current_count} items across {source_count} sources."
            ),
        )

    def _build_claim(
        self,
        trend: TopicTrend,
        items: list[IntelligenceItem],
        window_start: datetime,
        window_end: datetime,
    ) -> TrendClaim:
        representatives = _representative_items(items)
        evidence_refs = [
            EvidenceRef(
                item_id=item.id,
                source=item.source,
                title=item.title,
                url=item.canonical_url or item.url,
                reason=f"Representative item for topic {trend.topic}.",
            )
            for item in representatives
        ]
        confidence = _clamp(
            trend.momentum_score * 0.7 + min(trend.source_count, 3) / 10
        )
        claim_id = _claim_id(trend.topic, trend.trend_type.value, window_end)
        return TrendClaim(
            id=claim_id,
            topic=trend.topic,
            trend_type=trend.trend_type,
            claim=(
                f"Topic '{trend.topic}' shows {trend.trend_type.value} momentum "
                f"across {trend.source_count} sources."
            ),
            confidence=confidence,
            evidence_refs=evidence_refs,
            window_start=window_start,
            window_end=window_end,
            metrics={
                "current_count": float(trend.item_count),
                "previous_window_count": float(trend.previous_window_count),
                "growth_rate": trend.growth_rate,
                "source_count": float(trend.source_count),
                "momentum_score": trend.momentum_score,
            },
        )


def _topic_counts(items: list[IntelligenceItem]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[IntelligenceItem]] = defaultdict(list)
    for item in items:
        for topic in item.topics:
            grouped[topic].append(item)
    return {
        topic: _counts_for_items(topic_items)
        for topic, topic_items in grouped.items()
    }


def _counts_for_items(items: list[IntelligenceItem]) -> dict[str, Any]:
    counts: dict[str, Any] = {
        "item_count": len(items),
        "paper_count": 0,
        "repo_count": 0,
        "hn_count": 0,
        "company_count": 0,
        "sources": set(),
    }
    for item in items:
        counts["sources"].add(item.source.value)
        if item.item_type == ItemType.PAPER:
            counts["paper_count"] += 1
        if item.item_type == ItemType.REPO:
            counts["repo_count"] += 1
        if (
            item.source == SourceType.HACKERNEWS
            or item.item_type == ItemType.DISCUSSION
        ):
            counts["hn_count"] += 1
        if (
            item.source == SourceType.COMPANY_BLOGS
            or item.item_type == ItemType.COMPANY_UPDATE
        ):
            counts["company_count"] += 1
    return counts


def _item_time(item: IntelligenceItem) -> datetime:
    value = item.published_at or item.fetched_at
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _bounded_momentum(growth_rate: float, source_count: int, item_count: int) -> float:
    growth_component = max(0.0, min(0.5, (growth_rate + 1.0) / 4.0))
    source_component = min(source_count, 4) * 0.1
    volume_component = min(item_count, 5) * 0.04
    return _clamp(growth_component + source_component + volume_component)


def _average_novelty(items: list[IntelligenceItem]) -> float:
    if not items:
        return 0.0
    values = [item.scores.novelty if item.scores is not None else 1.0 for item in items]
    return _clamp(sum(values) / len(values))


def _classify_trend(
    current_count: int,
    previous_count: int,
    growth_rate: float,
    source_count: int,
) -> TrendType:
    if previous_count == 0 and current_count >= 2:
        return TrendType.EMERGING
    if growth_rate > 0.5 and current_count >= 2:
        return TrendType.ACCELERATING
    if growth_rate < -0.5:
        return TrendType.DECLINING
    if current_count == 1 and source_count == 1:
        return TrendType.NOISE
    if current_count > 0 and abs(growth_rate) <= 0.5:
        return TrendType.STABLE
    return TrendType.NOISE


def _representative_items(
    items: list[IntelligenceItem],
    limit: int = 3,
) -> list[IntelligenceItem]:
    return sorted(
        items,
        key=lambda item: (
            -(item.scores.final_score if item.scores is not None else 0.0),
            -_item_time(item).timestamp(),
            item.id,
        ),
    )[:limit]


def _claim_id(topic: str, trend_type: str, window_end: datetime) -> str:
    key = f"{topic}:{trend_type}:{window_end.date().isoformat()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"trend_{digest}"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
