from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from airi.models import ExtractionMetadata, ExtractionMethod, IntelligenceItem
from airi.normalize import normalize_for_matching

BUILT_IN_ENTITIES = [
    "OpenAI",
    "Anthropic",
    "Google DeepMind",
    "Meta AI",
    "Microsoft Research",
    "NVIDIA",
    "Hugging Face",
    "GitHub",
    "LangChain",
    "LlamaIndex",
    "Cursor",
    "Replit",
    "Cognition",
    "SWE-bench",
    "Terminal-Bench",
    "GAIA",
    "MLE-bench",
    "HumanEval",
    "LiveCodeBench",
    "MCP",
    "RAG",
    "LangGraph",
    "Claude Code",
    "GitHub Copilot",
    "OpenHands",
    "AutoGen",
    "CrewAI",
]


class EntityExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    entities: list[str] = Field(default_factory=list)
    matched_patterns: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    method: str = "rule"


class EntityExtractor:
    def __init__(self, watchlists_config: Any | None = None) -> None:
        self.entities = _dedupe(
            [*BUILT_IN_ENTITIES, *_watchlist_entities(watchlists_config)]
        )

    def extract(self, item: IntelligenceItem) -> EntityExtractionResult:
        text = normalize_for_matching(
            " ".join(
                [
                    item.title,
                    item.abstract or "",
                    item.content_snippet or "",
                    " ".join(item.keywords),
                ]
            )
        )
        entities = []
        patterns = []
        for entity in self.entities:
            pattern = normalize_for_matching(entity)
            if pattern and pattern in text:
                entities.append(entity)
                patterns.append(pattern)
        confidence = min(1.0, 0.4 + 0.2 * len(entities)) if entities else 0.0
        return EntityExtractionResult(
            item_id=item.id,
            entities=_dedupe(entities),
            matched_patterns=_dedupe(patterns),
            confidence=confidence,
        )

    def apply(self, items: list[IntelligenceItem]) -> list[IntelligenceItem]:
        updated = []
        for item in items:
            result = self.extract(item)
            metadata = ExtractionMetadata(
                method=ExtractionMethod.RULE,
                extractor_name="entity_extractor",
                extractor_version="v1",
                extracted_at=datetime.now(timezone.utc),
                confidence=result.confidence,
            )
            updated.append(
                item.model_copy(
                    update={
                        "entities": _dedupe([*item.entities, *result.entities]),
                        "extraction_metadata": [*item.extraction_metadata, metadata],
                    }
                )
            )
        return updated


def _watchlist_entities(watchlists_config: Any | None) -> list[str]:
    if watchlists_config is None:
        return []
    raw_watchlists = getattr(watchlists_config, "watchlists", None)
    if isinstance(watchlists_config, dict):
        raw_watchlists = watchlists_config.get("watchlists", [])
    entities: list[str] = []
    for watchlist in raw_watchlists or []:
        for field in ("keywords", "topics", "sources"):
            value = (
                getattr(watchlist, field, None)
                if not isinstance(watchlist, dict)
                else watchlist.get(field)
            )
            if isinstance(value, list):
                entities.extend(item for item in value if isinstance(item, str))
    return entities


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
