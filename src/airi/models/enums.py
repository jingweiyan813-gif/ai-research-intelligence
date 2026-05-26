from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    ARXIV = "arxiv"
    OPENREVIEW = "openreview"
    GITHUB = "github"
    HACKERNEWS = "hackernews"
    COMPANY_BLOGS = "company_blogs"
    DEVPOST = "devpost"
    RSS = "rss"
    UNKNOWN = "unknown"


class ItemType(str, Enum):
    PAPER = "paper"
    REPO = "repo"
    DISCUSSION = "discussion"
    COMPANY_UPDATE = "company_update"
    HACKATHON = "hackathon"
    ARTICLE = "article"
    UNKNOWN = "unknown"


class TrendType(str, Enum):
    EMERGING = "emerging"
    ACCELERATING = "accelerating"
    STABLE = "stable"
    DECLINING = "declining"
    NOISE = "noise"


class SuggestedAction(str, Enum):
    READ = "read"
    SKIM = "skim"
    TRY = "try"
    BOOKMARK = "bookmark"
    IGNORE = "ignore"
    IMPLEMENT = "implement"


class ExtractionMethod(str, Enum):
    RULE = "rule"
    LLM = "llm"
    MANUAL = "manual"
    MIXED = "mixed"
