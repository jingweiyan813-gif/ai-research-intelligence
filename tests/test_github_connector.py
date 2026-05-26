from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

from airi.connectors import GitHubConnector
from airi.models import ItemType, SourceType


def github_config(**overrides):  # type: ignore[no-untyped-def]
    config = {
        "queries": ["AI agent", "coding agent"],
        "min_stars": 100,
        "freshness_days": None,
        "max_results": 10,
        "enabled": True,
    }
    config.update(overrides)
    return config


def repo_record(**overrides):  # type: ignore[no-untyped-def]
    repo = {
        "id": 1,
        "node_id": "NODE_1",
        "full_name": "OpenAI/Codex",
        "html_url": "https://github.com/OpenAI/Codex/issues/1",
        "description": "AI coding agent",
        "stargazers_count": 1234,
        "forks_count": 56,
        "open_issues_count": 7,
        "pushed_at": "2026-01-10T00:00:00Z",
        "updated_at": "2026-01-11T00:00:00Z",
        "created_at": "2025-12-01T00:00:00Z",
        "topics": ["ai", "agents"],
        "language": "Python",
        "archived": False,
        "disabled": False,
        "license": {"spdx_id": "MIT"},
        "owner": {"login": "OpenAI"},
    }
    repo.update(overrides)
    return repo


def test_query_construction_includes_query_min_stars_and_pushed_date() -> None:
    connector = GitHubConnector(github_config())
    since = datetime(2026, 1, 1, tzinfo=timezone.utc)

    urls = connector.build_query_urls(since=since, limit=2)
    first_query = urllib.parse.parse_qs(urllib.parse.urlsplit(urls[0]).query)["q"][0]

    assert "AI agent" in first_query
    assert "stars:>=100" in first_query
    assert "pushed:>=2026-01-01" in first_query
    assert "per_page=2" in urls[0]


def test_limit_overrides_config_max_results(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = GitHubConnector(github_config(max_results=10))
    called_urls: list[str] = []

    def fake_fetch(url: str):  # type: ignore[no-untyped-def]
        called_urls.append(url)
        return {"items": [repo_record()]}

    monkeypatch.setattr(connector, "_fetch_json", fake_fetch)

    raw_items = connector.fetch_raw(limit=1)

    assert len(raw_items) == 1
    assert "per_page=1" in called_urls[0]


def test_token_header_is_included_when_provided() -> None:
    connector = GitHubConnector(github_config(), token="secret-token")

    assert connector._request_headers()["Authorization"] == "Bearer secret-token"


def test_unauthenticated_mode_works_without_token(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    connector = GitHubConnector(github_config(), token=None)

    assert "Authorization" not in connector._request_headers()


def test_repo_api_response_maps_to_raw_source_item(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = GitHubConnector(github_config(queries=["AI agent"]))
    monkeypatch.setattr(connector, "_fetch_json", lambda _: {"items": [repo_record()]})

    raw_items = connector.fetch_raw(
        since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        limit=2,
    )

    assert len(raw_items) == 1
    raw = raw_items[0]
    assert raw.source == SourceType.GITHUB
    assert raw.source_item_id == "OpenAI/Codex"
    assert raw.raw_url == "https://github.com/OpenAI/Codex"
    assert raw.raw_title == "OpenAI/Codex"
    assert raw.raw_text == "AI coding agent"
    assert raw.raw_payload["topics"] == ["ai", "agents"]


def test_normalize_maps_repo_metadata() -> None:
    connector = GitHubConnector(github_config())
    raw = connector._repo_to_raw(
        repo_record(html_url="https://github.com/OpenAI/Codex/blob/main/README.md"),
        fetched_at=datetime(2026, 1, 12, tzinfo=timezone.utc),
    )
    assert raw is not None

    item = connector.normalize(raw)

    assert item.source == SourceType.GITHUB
    assert item.item_type == ItemType.REPO
    assert item.title == "OpenAI/Codex"
    assert item.url == "https://github.com/OpenAI/Codex"
    assert item.canonical_url == "https://github.com/OpenAI/Codex"
    assert item.abstract == "AI coding agent"
    assert item.organizations == ["OpenAI"]
    assert item.repos == ["OpenAI/Codex"]
    assert item.keywords == ["ai", "agents", "Python"]
    assert item.signals.github is not None
    assert item.signals.github.stars == 1234
    assert item.signals.github.forks == 56
    assert item.signals.github.open_issues == 7
    assert item.signals.github.last_pushed_at == datetime(
        2026,
        1,
        10,
        tzinfo=timezone.utc,
    )
    assert item.published_at == datetime(2025, 12, 1, tzinfo=timezone.utc)


def test_archived_disabled_and_low_star_repos_are_filtered(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = GitHubConnector(github_config(min_stars=100))
    monkeypatch.setattr(
        connector,
        "_fetch_json",
        lambda _: {
            "items": [
                repo_record(full_name="A/Archived", archived=True),
                repo_record(full_name="B/Disabled", disabled=True),
                repo_record(full_name="C/Small", stargazers_count=10),
                repo_record(full_name="D/Good", stargazers_count=101),
            ]
        },
    )

    raw_items = connector.fetch_raw(limit=10)

    assert [item.source_item_id for item in raw_items] == ["D/Good"]


def test_old_pushed_at_repos_are_filtered_by_freshness(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connector = GitHubConnector(github_config())
    monkeypatch.setattr(
        connector,
        "_fetch_json",
        lambda _: {
            "items": [
                repo_record(full_name="A/Old", pushed_at="2020-01-01T00:00:00Z"),
                repo_record(full_name="B/New", pushed_at="2026-01-02T00:00:00Z"),
            ]
        },
    )

    raw_items = connector.fetch_raw(
        since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        limit=10,
    )

    assert [item.source_item_id for item in raw_items] == ["B/New"]


def test_malformed_repo_records_are_skipped() -> None:
    connector = GitHubConnector(github_config())

    assert connector._repo_to_raw({}, fetched_at=datetime.now(timezone.utc)) is None
