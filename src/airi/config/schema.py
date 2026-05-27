from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceConfig(StrictConfigModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    enabled: bool = False
    type: str = Field(min_length=1)
    url: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    max_results: int = Field(default=10, gt=0)
    freshness_days: int | None = Field(default=None, gt=0)
    min_stars: int | None = Field(default=None, ge=0)
    keywords: list[str] = Field(default_factory=list)
    min_score: int | None = Field(default=None, ge=0)
    feeds: list[dict[str, str]] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)
    days_ahead: int | None = Field(default=None, gt=0)
    listing_urls: list[str] = Field(default_factory=list)


class SourcesConfig(StrictConfigModel):
    sources: list[SourceConfig]

    @model_validator(mode="after")
    def require_enabled_source(self) -> SourcesConfig:
        if not any(source.enabled for source in self.sources):
            raise ValueError("sources.yml must contain at least one enabled source")
        return self


class TopicConfig(StrictConfigModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    keywords: list[str] = Field(default_factory=list)


class TopicsConfig(StrictConfigModel):
    primary_topics: list[TopicConfig]
    negative_topics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_primary_topic(self) -> TopicsConfig:
        if not self.primary_topics:
            raise ValueError("topics.yml must contain at least one primary topic")
        return self


class ScoringWeights(StrictConfigModel):
    topic_relevance: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.0)
    momentum: float = Field(ge=0.0, le=1.0)
    cross_source_correlation: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    popularity: float = Field(ge=0.0, le=1.0)
    personal_relevance: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_sum_to_one(self) -> ScoringWeights:
        total = sum(self.model_dump().values())
        if abs(total - 1.0) > 0.000001:
            raise ValueError("scoring weights must sum to 1.0")
        return self


class RankingProfile(ScoringWeights):
    pass


class ScoringThresholds(StrictConfigModel):
    minimum_score: float = Field(ge=0.0, le=1.0)
    strong_signal: float = Field(ge=0.0, le=1.0)
    trend_candidate: float = Field(ge=0.0, le=1.0)


class ScoringLimits(StrictConfigModel):
    max_items_per_source: int = Field(gt=0)
    max_report_items: int = Field(gt=0)
    max_trend_candidates: int = Field(gt=0)


class ScoringConfig(StrictConfigModel):
    active_profile: str = Field(min_length=1)
    ranking_profiles: dict[str, RankingProfile]
    thresholds: ScoringThresholds
    limits: ScoringLimits

    @model_validator(mode="before")
    @classmethod
    def migrate_flat_weights(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "ranking_profiles" not in data and "weights" in data:
            migrated = dict(data)
            migrated["active_profile"] = migrated.get("active_profile", "item_baseline")
            migrated["ranking_profiles"] = {
                migrated["active_profile"]: migrated.pop("weights")
            }
            return migrated
        return data

    @model_validator(mode="after")
    def require_active_profile(self) -> ScoringConfig:
        if not self.ranking_profiles:
            raise ValueError("scoring.yml must define at least one ranking profile")
        if self.active_profile not in self.ranking_profiles:
            raise ValueError("active_profile must reference a ranking profile")
        return self

    @property
    def weights(self) -> RankingProfile:
        return self.ranking_profiles[self.active_profile]

    def profile_weights(self, profile_name: str | None = None) -> RankingProfile:
        selected = profile_name or self.active_profile
        try:
            return self.ranking_profiles[selected]
        except KeyError as exc:
            raise ValueError(f"Unknown ranking profile: {selected}") from exc


class ProfileBody(StrictConfigModel):
    name: str = Field(min_length=1)
    email: str | None = None
    timezone: str = "UTC"
    interests: list[str] = Field(default_factory=list)


class UserProfileConfig(StrictConfigModel):
    profile: ProfileBody


class EmailBody(StrictConfigModel):
    enabled: bool = False
    provider: str = Field(min_length=1)
    from_address: str | None = None
    to_addresses: list[str] = Field(default_factory=list)
    subject_prefix: str = "[AIRI]"
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, gt=0)
    username: str | None = None
    password: str | None = None
    api_key: str | None = None


class EmailExampleConfig(StrictConfigModel):
    email: EmailBody


class WatchlistConfig(StrictConfigModel):
    name: str = Field(min_length=1)
    topics: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class WatchlistsConfig(StrictConfigModel):
    watchlists: list[WatchlistConfig] = Field(default_factory=list)


class AppConfig(StrictConfigModel):
    sources: SourcesConfig
    topics: TopicsConfig
    scoring: ScoringConfig
    profile: UserProfileConfig
    email: EmailExampleConfig
    watchlists: WatchlistsConfig
    local_overrides: dict[str, bool]

    def sanitized_summary(self) -> dict[str, Any]:
        return {
            "enabled_sources": [
                source.id for source in self.sources.sources if source.enabled
            ],
            "primary_topics": [topic.id for topic in self.topics.primary_topics],
            "active_ranking_profile": self.scoring.active_profile,
            "ranking_profiles": {
                name: profile.model_dump()
                for name, profile in self.scoring.ranking_profiles.items()
            },
            "local_overrides": self.local_overrides,
        }
