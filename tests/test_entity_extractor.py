from __future__ import annotations

from airi.intelligence import EntityExtractor
from tests.factories import make_item


def test_extracts_known_companies_tools_and_benchmarks() -> None:
    item = make_item(
        title="OpenAI releases MCP tool",
        abstract="Evaluation on SWE-bench with GitHub Copilot.",
    )

    result = EntityExtractor().extract(item)

    assert "OpenAI" in result.entities
    assert "MCP" in result.entities
    assert "SWE-bench" in result.entities
    assert "GitHub Copilot" in result.entities


def test_supports_watchlist_config() -> None:
    watchlists = {"watchlists": [{"keywords": ["CustomLab"]}]}
    item = make_item(title="CustomLab launches agent")

    result = EntityExtractor(watchlists).extract(item)

    assert "CustomLab" in result.entities


def test_apply_preserves_existing_entities_and_appends_metadata() -> None:
    item = make_item(
        title="Anthropic Claude Code",
        abstract=None,
        entities=["Existing"],
    )

    updated = EntityExtractor().apply([item])[0]

    assert updated.entities == ["Existing", "Anthropic", "Claude Code"]
    assert updated.extraction_metadata[-1].extractor_name == "entity_extractor"


def test_confidence_is_deterministic() -> None:
    item = make_item(title="OpenAI MCP")
    extractor = EntityExtractor()

    assert extractor.extract(item).confidence == extractor.extract(item).confidence
