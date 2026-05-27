from __future__ import annotations

from typing import Any

from airi.intelligence import PaperRepoLinker
from airi.models import ItemType, SourceType
from airi.models.item import IntelligenceItem
from tests.factories import make_item


def _repo(**kwargs: Any) -> IntelligenceItem:
    return make_item(source=SourceType.GITHUB, item_type=ItemType.REPO, **kwargs)


def test_links_by_exact_repo_mention() -> None:
    paper = make_item(
        item_id="paper",
        title="CodeAgent Paper",
        abstract="The implementation is available at openai/codeagent.",
    )
    repo = _repo(item_id="repo", title="openai/codeagent", repos=["openai/codeagent"])

    links = PaperRepoLinker().link([paper, repo])

    assert links[0].confidence >= 0.9
    assert "explicitly mentions" in links[0].reason


def test_links_by_strong_token_overlap() -> None:
    paper = make_item(item_id="paper", title="Sparse Memory Planner for Coding Agents")
    repo = _repo(
        item_id="repo",
        title="sparse-memory-planner",
        abstract="Sparse memory planner implementation for coding agents.",
    )

    links = PaperRepoLinker().link([paper, repo])

    assert links
    assert links[0].confidence >= 0.5


def test_links_by_shared_distinctive_entity() -> None:
    paper = make_item(
        item_id="paper",
        abstract="Study of verified benchmark.",
        entities=["SWE-bench Verified"],
    )
    repo = _repo(
        item_id="repo",
        title="verified solver",
        abstract="Solver for tasks.",
        entities=["SWE-bench Verified"],
    )

    links = PaperRepoLinker().link([paper, repo])

    assert links[0].matched_terms == ["SWE-bench Verified"]


def test_does_not_link_generic_terms_only() -> None:
    paper = make_item(
        item_id="paper",
        title="AI agent framework",
        abstract=None,
        entities=["agent"],
    )
    repo = _repo(
        item_id="repo",
        title="LLM RAG benchmark",
        abstract=None,
        entities=["agent"],
    )

    assert PaperRepoLinker().link([paper, repo]) == []


def test_confidence_and_reason_are_present() -> None:
    paper = make_item(item_id="paper", url="https://arxiv.org/abs/2401.12345")
    repo = _repo(item_id="repo", keywords=["2401.12345"])

    link = PaperRepoLinker().link([paper, repo])[0]

    assert link.confidence > 0
    assert link.reason
