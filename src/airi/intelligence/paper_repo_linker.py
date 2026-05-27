from __future__ import annotations

import re
from itertools import product

from pydantic import BaseModel, ConfigDict, Field

from airi.models import IntelligenceItem, ItemType
from airi.normalize import normalize_for_matching

_GENERIC_TERMS = {
    "agent",
    "agents",
    "llm",
    "llms",
    "rag",
    "ai",
    "benchmark",
    "framework",
    "model",
    "models",
    "tool",
    "tools",
}
_ARXIV_ID_RE = re.compile(r"\b\d{4}\.\d{4,5}(?:v\d+)?\b")


class PaperRepoLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_item_id: str = Field(min_length=1)
    repo_item_id: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
    matched_terms: list[str] = Field(default_factory=list)


class PaperRepoLinker:
    def link(self, items: list[IntelligenceItem]) -> list[PaperRepoLink]:
        papers = [item for item in items if item.item_type == ItemType.PAPER]
        repos = [item for item in items if item.item_type == ItemType.REPO]
        links = []
        for paper, repo in product(papers, repos):
            link = _link_pair(paper, repo)
            if link is not None:
                links.append(link)
        return sorted(
            links,
            key=lambda link: (-link.confidence, link.paper_item_id, link.repo_item_id),
        )


def _link_pair(
    paper: IntelligenceItem,
    repo: IntelligenceItem,
) -> PaperRepoLink | None:
    paper_text = _item_text(paper)
    repo_text = _item_text(repo)
    repo_names = _repo_names(repo)
    for repo_name in repo_names:
        normalized_repo = normalize_for_matching(repo_name)
        if normalized_repo and normalized_repo in paper_text:
            return PaperRepoLink(
                paper_item_id=paper.id,
                repo_item_id=repo.id,
                confidence=0.95,
                reason="Paper text explicitly mentions repository name.",
                matched_terms=[repo_name],
            )

    arxiv_ids = _arxiv_ids(paper)
    matched_arxiv = [arxiv_id for arxiv_id in arxiv_ids if arxiv_id in repo_text]
    if matched_arxiv:
        return PaperRepoLink(
            paper_item_id=paper.id,
            repo_item_id=repo.id,
            confidence=0.9,
            reason="Repository metadata mentions paper arXiv id.",
            matched_terms=matched_arxiv,
        )

    paper_tokens = _distinctive_tokens(paper.title, paper.abstract or "")
    repo_tokens = _distinctive_tokens(
        repo.title,
        repo.abstract or repo.content_snippet or "",
    )
    overlap = sorted(paper_tokens & repo_tokens)
    denominator = max(min(len(paper_tokens), len(repo_tokens)), 1)
    overlap_ratio = len(overlap) / denominator
    if len(overlap) >= 3 and overlap_ratio >= 0.5:
        return PaperRepoLink(
            paper_item_id=paper.id,
            repo_item_id=repo.id,
            confidence=min(0.8, 0.45 + overlap_ratio * 0.35),
            reason="Paper and repository titles/descriptions share distinctive terms.",
            matched_terms=overlap,
        )

    shared_entities = sorted(
        set(paper.entities) & set(repo.entities) - _GENERIC_TERMS
    )
    if shared_entities:
        return PaperRepoLink(
            paper_item_id=paper.id,
            repo_item_id=repo.id,
            confidence=0.55,
            reason="Paper and repository share distinctive extracted entities.",
            matched_terms=shared_entities,
        )
    return None


def _item_text(item: IntelligenceItem) -> str:
    return normalize_for_matching(
        " ".join(
            [
                item.title,
                item.abstract or "",
                item.content_snippet or "",
                " ".join(item.keywords),
                " ".join(item.entities),
                " ".join(item.repos),
                " ".join(item.papers),
                item.url,
                item.canonical_url or "",
            ]
        )
    )


def _repo_names(repo: IntelligenceItem) -> list[str]:
    names = [repo.title, *repo.repos]
    if repo.canonical_url and "github.com" in repo.canonical_url.lower():
        parts = [part for part in repo.canonical_url.rstrip("/").split("/") if part]
        if len(parts) >= 2:
            names.append("/".join(parts[-2:]))
            names.append(parts[-1])
    return _dedupe([name for name in names if name])


def _arxiv_ids(paper: IntelligenceItem) -> list[str]:
    text = " ".join([paper.url, paper.canonical_url or "", *paper.papers])
    return sorted(set(_ARXIV_ID_RE.findall(text)))


def _distinctive_tokens(*parts: str) -> set[str]:
    text = normalize_for_matching(" ".join(parts))
    return {
        token
        for token in text.replace("/", " ").split()
        if len(token) >= 4 and token not in _GENERIC_TERMS and not token.isdigit()
    }


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
