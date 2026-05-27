from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from airi.models import ExtractionMetadata, ExtractionMethod, IntelligenceItem
from airi.normalize import normalize_for_matching


class TopicExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    topics: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    negative_matches: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    method: str = "rule"


class TopicExtractor:
    def __init__(self, topics_config: Any) -> None:
        self.primary_topics = _get_topics(topics_config)
        self.negative_topics = _get_negative_topics(topics_config)

    def extract(self, item: IntelligenceItem) -> TopicExtractionResult:
        fields = self._matching_fields(item)
        weighted_matches: dict[str, float] = {}
        matched_keywords: list[str] = []

        for topic_id, keywords in self.primary_topics.items():
            score = 0.0
            for keyword in keywords:
                normalized_keyword = normalize_for_matching(keyword)
                if not normalized_keyword:
                    continue
                if normalized_keyword in fields["title"]:
                    score += 0.5
                    matched_keywords.append(keyword)
                if normalized_keyword in fields["abstract"]:
                    score += 0.3
                    matched_keywords.append(keyword)
                if normalized_keyword in fields["keywords"]:
                    score += 0.2
                    matched_keywords.append(keyword)
            if score > 0:
                weighted_matches[topic_id] = score

        negative_matches = []
        combined = " ".join(fields.values())
        for negative in self.negative_topics:
            if normalize_for_matching(negative) in combined:
                negative_matches.append(negative)

        topics = list(weighted_matches.keys())
        confidence = (
            min(1.0, sum(weighted_matches.values())) if weighted_matches else 0.0
        )
        return TopicExtractionResult(
            item_id=item.id,
            topics=topics,
            matched_keywords=_dedupe(matched_keywords),
            negative_matches=_dedupe(negative_matches),
            confidence=confidence,
        )

    def apply(self, items: list[IntelligenceItem]) -> list[IntelligenceItem]:
        updated = []
        for item in items:
            result = self.extract(item)
            metadata = ExtractionMetadata(
                method=ExtractionMethod.RULE,
                extractor_name="topic_extractor",
                extractor_version="v1",
                extracted_at=datetime.now(timezone.utc),
                confidence=result.confidence,
            )
            updated.append(
                item.model_copy(
                    update={
                        "topics": _dedupe([*item.topics, *result.topics]),
                        "extraction_metadata": [*item.extraction_metadata, metadata],
                    }
                )
            )
        return updated

    def _matching_fields(self, item: IntelligenceItem) -> dict[str, str]:
        return {
            "title": normalize_for_matching(item.title),
            "abstract": normalize_for_matching(
                " ".join([item.abstract or "", item.content_snippet or ""])
            ),
            "keywords": normalize_for_matching(
                " ".join([*item.keywords, *item.entities])
            ),
        }


def _get_topics(topics_config: Any) -> dict[str, list[str]]:
    raw_topics = getattr(topics_config, "primary_topics", None)
    if isinstance(topics_config, dict):
        raw_topics = topics_config.get("primary_topics", [])
    topics = {}
    for topic in raw_topics or []:
        topic_id = (
            getattr(topic, "id", None)
            if not isinstance(topic, dict)
            else topic.get("id")
        )
        keywords = (
            getattr(topic, "keywords", None)
            if not isinstance(topic, dict)
            else topic.get("keywords")
        )
        if isinstance(topic_id, str):
            topics[topic_id] = [
                word for word in keywords or [] if isinstance(word, str)
            ]
    return topics


def _get_negative_topics(topics_config: Any) -> list[str]:
    if isinstance(topics_config, dict):
        value = topics_config.get("negative_topics", [])
    else:
        value = getattr(topics_config, "negative_topics", [])
    return [item for item in value if isinstance(item, str)]


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
