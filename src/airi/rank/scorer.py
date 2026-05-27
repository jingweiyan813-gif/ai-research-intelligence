from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from airi.models import IntelligenceItem, ItemType, ScoreBreakdown, ScoreBundle
from airi.normalize import normalize_for_matching

DEFAULT_WEIGHTS = {
    "topic_relevance": 0.24,
    "quality": 0.18,
    "momentum": 0.14,
    "cross_source_correlation": 0.0,
    "novelty": 0.14,
    "freshness": 0.10,
    "popularity": 0.08,
    "personal_relevance": 0.12,
}
DEFAULT_FRESHNESS_HALF_LIFE_DAYS = 30.0


class ItemScorer:
    def __init__(
        self,
        scoring_config: Any,
        profile_config: Any | None = None,
        ranking_profile: str | None = None,
    ) -> None:
        self.scoring_config = scoring_config
        self.profile_config = profile_config
        self.weights = resolve_scoring_weights(scoring_config, ranking_profile)
        self.profile_interests = _profile_interests(profile_config)

    def score(self, item: IntelligenceItem) -> ScoreBundle:
        breakdowns: list[ScoreBreakdown] = []
        topic_relevance = self._topic_relevance(item, breakdowns)
        quality = self._quality(item, breakdowns)
        freshness = self._freshness(item, breakdowns)
        popularity = self._popularity(item, breakdowns)
        novelty = self._novelty(item, breakdowns)
        momentum = self._placeholder(
            item,
            breakdowns,
            "momentum",
            "趋势引擎尚未参与该条目评分，动量分暂为 0。",
        )
        personal_relevance = self._personal_relevance(item, breakdowns)
        cross_source_correlation = self._placeholder(
            item,
            breakdowns,
            "cross_source_correlation",
            "跨源关联尚未参与该条目评分，关联分暂为 0。",
        )
        weighted_sum = (
            self.weights.get("topic_relevance", 0.0) * topic_relevance
            + self.weights.get("quality", 0.0) * quality
            + self.weights.get("freshness", 0.0) * freshness
            + self.weights.get("popularity", 0.0) * popularity
            + self.weights.get("novelty", 0.0) * novelty
            + self.weights.get("momentum", 0.0) * momentum
            + self.weights.get("cross_source_correlation", 0.0)
            * cross_source_correlation
            + self.weights.get("personal_relevance", 0.0) * personal_relevance
        )
        final_score = _clamp(weighted_sum)
        breakdowns.append(
            ScoreBreakdown(
                dimension="final_score",
                score=final_score,
                reason="根据当前排序策略的配置权重加权计算。",
                evidence_item_ids=[item.id],
            )
        )
        return ScoreBundle(
            topic_relevance=topic_relevance,
            quality=quality,
            freshness=freshness,
            popularity=popularity,
            novelty=novelty,
            momentum=momentum,
            personal_relevance=personal_relevance,
            cross_source_correlation=cross_source_correlation,
            final_score=final_score,
            breakdowns=breakdowns,
        )

    def _topic_relevance(
        self,
        item: IntelligenceItem,
        breakdowns: list[ScoreBreakdown],
    ) -> float:
        score = min(0.8, 0.25 * len(item.topics))
        matching_interests = [
            topic for topic in item.topics if topic in self.profile_interests
        ]
        if matching_interests:
            score += 0.2
        text = normalize_for_matching(" ".join([*item.keywords, *item.entities]))
        if any("negative" in token or "unrelated" in token for token in text.split()):
            score -= 0.2
        score = _clamp(score)
        reason = (
            f"命中 {len(item.topics)} 个主题，"
            f"匹配 {len(matching_interests)} 个个人兴趣。"
        )
        breakdowns.append(_breakdown(item, "topic_relevance", score, reason))
        return score

    def _quality(  # noqa: C901
        self,
        item: IntelligenceItem,
        breakdowns: list[ScoreBreakdown],
    ) -> float:
        score = 0.2
        reasons = []
        if item.title:
            score += 0.1
            reasons.append("标题信息完整")
        if item.abstract or item.content_snippet:
            score += 0.15
            reasons.append("描述信息完整")
        if item.item_type == ItemType.PAPER and item.signals.paper is not None:
            if item.signals.paper.paper_categories:
                score += 0.2
                reasons.append("包含论文分类信息")
            if item.signals.paper.venue:
                score += 0.2
                reasons.append("包含 venue 信息")
        elif item.item_type == ItemType.REPO and item.signals.github is not None:
            stars = item.signals.github.stars or 0
            forks = item.signals.github.forks or 0
            score += min(0.3, math.log10(stars + 1) / 12)
            score += min(0.15, math.log10(forks + 1) / 15)
            if item.signals.github.last_pushed_at is not None:
                score += 0.1
            reasons.append("包含 GitHub repository metadata")
        elif (
            item.item_type == ItemType.DISCUSSION
            and item.signals.community is not None
        ):
            score += min(0.35, (item.signals.community.hn_score or 0) / 500)
            score += min(0.15, (item.signals.community.hn_comments or 0) / 300)
            reasons.append("包含 Hacker News 互动信号")
        elif (
            item.item_type == ItemType.COMPANY_UPDATE
            and item.signals.company is not None
        ):
            if item.signals.company.is_official_announcement:
                score += 0.35
            if item.signals.company.company_name:
                score += 0.15
            reasons.append("官方公司 / 实验室动态")
        elif (
            item.item_type == ItemType.HACKATHON
            and item.signals.hackathon is not None
        ):
            if item.signals.hackathon.deadline_at is not None:
                score += 0.2
            if item.signals.hackathon.is_remote is not None:
                score += 0.1
            if item.signals.hackathon.prize_amount:
                score += 0.15
            reasons.append("包含黑客松 metadata")
        score = _clamp(score)
        breakdowns.append(
            _breakdown(
                item,
                "quality",
                score,
                "；".join(reasons) or "基础 metadata 完整",
            )
        )
        return score

    def _freshness(
        self,
        item: IntelligenceItem,
        breakdowns: list[ScoreBreakdown],
    ) -> float:
        reference = item.published_at or item.fetched_at
        age_days = max(
            0.0,
            (datetime.now(timezone.utc) - reference).total_seconds() / 86400,
        )
        half_life = _config_value(
            self.scoring_config,
            "freshness_half_life_days",
            DEFAULT_FRESHNESS_HALF_LIFE_DAYS,
        )
        score = _clamp(0.5 ** (age_days / float(half_life)))
        breakdowns.append(
            _breakdown(item, "freshness", score, f"距今约 {age_days:.1f} 天。")
        )
        return score

    def _popularity(
        self,
        item: IntelligenceItem,
        breakdowns: list[ScoreBreakdown],
    ) -> float:
        score = 0.2
        reason = "暂无明显热度信号，使用较低的中性热度分。"
        if item.signals.github is not None:
            stars = item.signals.github.stars or 0
            forks = item.signals.github.forks or 0
            score = _clamp(math.log10(stars + 1) / 5 + math.log10(forks + 1) / 10)
            reason = f"GitHub 星标数={stars}，fork 数={forks}。"
        elif item.signals.community is not None:
            hn_score = item.signals.community.hn_score or 0
            comments = item.signals.community.hn_comments or 0
            score = _clamp(hn_score / 500 + comments / 500)
            reason = f"HN 分数={hn_score}，评论数={comments}。"
        elif (
            item.signals.paper is not None
            and item.signals.paper.citation_count is not None
        ):
            citations = item.signals.paper.citation_count
            score = _clamp(math.log10(citations + 1) / 4)
            reason = f"引用数={citations}。"
        breakdowns.append(_breakdown(item, "popularity", score, reason))
        return score

    def _novelty(
        self,
        item: IntelligenceItem,
        breakdowns: list[ScoreBreakdown],
    ) -> float:
        score = item.scores.novelty if item.scores is not None else 1.0
        score = _clamp(score)
        breakdowns.append(
            _breakdown(
                item,
                "novelty",
                score,
                "该条目暂无历史记录，按新条目处理。",
            )
        )
        return score

    def _personal_relevance(
        self,
        item: IntelligenceItem,
        breakdowns: list[ScoreBreakdown],
    ) -> float:
        text = normalize_for_matching(
            " ".join(
                [
                    item.title,
                    item.abstract or "",
                    " ".join(item.keywords),
                    " ".join(item.entities),
                    " ".join(item.topics),
                ]
            )
        )
        matches = [
            interest
            for interest in self.profile_interests
            if normalize_for_matching(interest) in text
        ]
        score = _clamp(0.2 + 0.25 * len(matches)) if self.profile_interests else 0.3
        reason = (
            "未命中个人兴趣配置。"
            if not matches
            else f"命中个人兴趣配置：{', '.join(matches)}。"
        )
        breakdowns.append(
            _breakdown(
                item,
                "personal_relevance",
                score,
                reason,
            )
        )
        return score

    def _placeholder(
        self,
        item: IntelligenceItem,
        breakdowns: list[ScoreBreakdown],
        dimension: str,
        reason: str,
    ) -> float:
        breakdowns.append(_breakdown(item, dimension, 0.0, reason))
        return 0.0


def _breakdown(
    item: IntelligenceItem,
    dimension: str,
    score: float,
    reason: str,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        dimension=dimension,
        score=_clamp(score),
        reason=reason,
        evidence_item_ids=[item.id],
    )


def resolve_scoring_weights(
    scoring_config: Any,
    ranking_profile: str | None = None,
) -> dict[str, float]:
    if hasattr(scoring_config, "profile_weights"):
        weights = scoring_config.profile_weights(ranking_profile)
        return _weights_to_dict(weights)
    profiles = _config_value(scoring_config, "ranking_profiles", None)
    if isinstance(profiles, dict):
        selected = ranking_profile or str(
            _config_value(scoring_config, "active_profile", "intelligence")
        )
        if selected not in profiles:
            raise ValueError(f"Unknown ranking profile: {selected}")
        return _weights_to_dict(profiles[selected])
    weights = _config_value(scoring_config, "weights", None)
    if weights is None:
        return DEFAULT_WEIGHTS.copy()
    return _weights_to_dict(weights)


def _weights_to_dict(weights: Any) -> dict[str, float]:
    if hasattr(weights, "model_dump"):
        values = weights.model_dump()
    elif isinstance(weights, dict):
        values = weights
    else:
        values = {}
    return {
        key: float(values.get(key, DEFAULT_WEIGHTS.get(key, 0.0)))
        for key in DEFAULT_WEIGHTS
    }


def _profile_interests(profile_config: Any | None) -> list[str]:
    if profile_config is None:
        return []
    profile = _config_value(profile_config, "profile", profile_config)
    interests = _config_value(profile, "interests", [])
    return [interest for interest in interests if isinstance(interest, str)]


def _config_value(config: Any, name: str, default: Any) -> Any:
    if isinstance(config, dict):
        return config.get(name, default)
    return getattr(config, name, default)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
