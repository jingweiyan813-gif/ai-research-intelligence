from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SignalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommonSignals(SignalModel):
    freshness_days: float | None = Field(default=None, ge=0.0)
    source_importance: float = Field(default=0.0, ge=0.0, le=1.0)


class PaperSignals(SignalModel):
    paper_categories: list[str] = Field(default_factory=list)
    venue: str | None = None
    has_code: bool | None = None
    citation_count: int | None = Field(default=None, ge=0)


class GitHubSignals(SignalModel):
    stars: int | None = Field(default=None, ge=0)
    forks: int | None = Field(default=None, ge=0)
    recent_commits: int | None = Field(default=None, ge=0)
    open_issues: int | None = Field(default=None, ge=0)
    last_pushed_at: datetime | None = None


class CommunitySignals(SignalModel):
    hn_score: int | None = Field(default=None, ge=0)
    hn_comments: int | None = Field(default=None, ge=0)


class HackathonSignals(SignalModel):
    deadline_at: datetime | None = None
    prize_amount: str | None = None
    is_remote: bool | None = None


class CompanySignals(SignalModel):
    company_name: str | None = None
    is_official_announcement: bool = False


class SignalBundle(SignalModel):
    common: CommonSignals = Field(default_factory=CommonSignals)
    paper: PaperSignals | None = None
    github: GitHubSignals | None = None
    community: CommunitySignals | None = None
    hackathon: HackathonSignals | None = None
    company: CompanySignals | None = None
