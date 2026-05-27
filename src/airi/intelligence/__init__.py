from airi.intelligence.cross_source import CrossSourceAnalyzer, CrossSourceSignal
from airi.intelligence.dedupe import DedupeEngine, DedupeResult, DuplicateGroup
from airi.intelligence.entity_extractor import EntityExtractionResult, EntityExtractor
from airi.intelligence.novelty import NoveltyResult, NoveltyTracker
from airi.intelligence.paper_repo_linker import PaperRepoLink, PaperRepoLinker
from airi.intelligence.topic_extractor import TopicExtractionResult, TopicExtractor
from airi.intelligence.trend_engine import TrendAnalysisResult, TrendEngine

__all__ = [
    "CrossSourceAnalyzer",
    "CrossSourceSignal",
    "DedupeEngine",
    "DedupeResult",
    "DuplicateGroup",
    "EntityExtractionResult",
    "EntityExtractor",
    "NoveltyResult",
    "NoveltyTracker",
    "PaperRepoLink",
    "PaperRepoLinker",
    "TopicExtractionResult",
    "TopicExtractor",
    "TrendAnalysisResult",
    "TrendEngine",
]
