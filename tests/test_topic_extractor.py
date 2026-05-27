from __future__ import annotations

from airi.intelligence import TopicExtractor
from tests.factories import make_item


def topics_config() -> dict[str, object]:
    return {
        "primary_topics": [
            {"id": "ai_agents", "keywords": ["AI agent", "agent"]},
            {"id": "coding_agents", "keywords": ["coding agent", "code"]},
        ],
        "negative_topics": ["crypto trading"],
    }


def test_extracts_expected_topics_from_fields() -> None:
    item = make_item(
        title="New AI agent",
        abstract="A coding agent for code review.",
        keywords=["code"],
    )

    result = TopicExtractor(topics_config()).extract(item)

    assert result.topics == ["ai_agents", "coding_agents"]
    assert "AI agent" in result.matched_keywords
    assert result.confidence > 0


def test_negative_topic_matches_recorded() -> None:
    item = make_item(title="AI agent for crypto trading")

    result = TopicExtractor(topics_config()).extract(item)

    assert result.negative_matches == ["crypto trading"]


def test_apply_preserves_existing_topics_and_appends_metadata() -> None:
    item = make_item(title="AI agent", topics=["existing"])

    updated = TopicExtractor(topics_config()).apply([item])[0]

    assert updated.topics == ["existing", "ai_agents"]
    assert updated.extraction_metadata[-1].extractor_name == "topic_extractor"
    assert updated.extraction_metadata[-1].confidence is not None


def test_confidence_is_deterministic() -> None:
    item = make_item(title="AI agent", abstract="agent agent")
    extractor = TopicExtractor(topics_config())

    assert extractor.extract(item).confidence == extractor.extract(item).confidence
