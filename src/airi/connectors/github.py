from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from airi.connectors.base import BaseConnector
from airi.models import (
    CommonSignals,
    GitHubSignals,
    IntelligenceItem,
    ItemType,
    RawSourceItem,
    SignalBundle,
    SourceMetadata,
    SourceType,
    build_item_id,
)
from airi.normalize import (
    canonicalize_github_url,
    content_fingerprint,
    normalize_text,
    source_payload_hash,
)

GITHUB_SEARCH_API_URL = "https://api.github.com/search/repositories"
USER_AGENT = "ai-research-intelligence"


class GitHubConnector(BaseConnector):
    name = "github"
    source = SourceType.GITHUB
    connector_version = "v1"

    def __init__(self, config: Any, token: str | None = None) -> None:
        self.config = config
        self.queries = list(_get_config_value(config, "queries", []))
        self.min_stars = _get_config_value(config, "min_stars", None)
        self.freshness_days = _get_config_value(config, "freshness_days", None)
        self.max_results = int(_get_config_value(config, "max_results", 10))
        self.enabled = bool(_get_config_value(config, "enabled", True))
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")

    def fetch_raw(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[RawSourceItem]:
        if not self.enabled:
            return []
        effective_limit = limit if limit is not None else self.max_results
        cutoff = self._cutoff_datetime(since)
        fetched_at = datetime.now(timezone.utc)
        raw_items: list[RawSourceItem] = []
        seen_ids: set[str] = set()

        for url in self.build_query_urls(since=since, limit=effective_limit):
            response = self._fetch_json(url)
            items = response.get("items", [])
            if not isinstance(items, list):
                continue
            for repo in items:
                if not isinstance(repo, dict):
                    continue
                raw_item = self._repo_to_raw(repo, fetched_at=fetched_at)
                if raw_item is None:
                    continue
                pushed_at = _parse_datetime(raw_item.raw_payload.get("pushed_at"))
                if cutoff is not None and pushed_at is not None and pushed_at < cutoff:
                    continue
                stable_key = raw_item.source_item_id or raw_item.raw_url
                if stable_key in seen_ids:
                    continue
                seen_ids.add(stable_key)
                raw_items.append(raw_item)
                if len(raw_items) >= effective_limit:
                    return raw_items
        return raw_items

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        payload_hash = source_payload_hash(raw.raw_payload)
        full_name = normalize_text(
            str(raw.raw_payload.get("full_name") or raw.raw_title)
        )
        description = normalize_text(raw.raw_text or "")
        canonical_url = canonicalize_github_url(raw.raw_url)
        pushed_at = _parse_datetime(raw.raw_payload.get("pushed_at"))
        created_at = _parse_datetime(raw.raw_payload.get("created_at"))
        topics = _string_list(raw.raw_payload.get("topics"))
        language = raw.raw_payload.get("language")
        keywords = list(topics)
        if isinstance(language, str) and language:
            keywords.append(language)
        owner_login = _owner_login(raw.raw_payload)
        fetched_at = raw.fetched_at
        freshness_days = None
        if pushed_at is not None:
            freshness_days = max(0.0, (fetched_at - pushed_at).total_seconds() / 86400)

        return IntelligenceItem(
            id=build_item_id(SourceType.GITHUB, full_name or canonical_url),
            source=SourceType.GITHUB,
            item_type=ItemType.REPO,
            title=full_name,
            url=canonical_url,
            canonical_url=canonical_url,
            abstract=description or None,
            content_snippet=description or None,
            authors=[],
            organizations=[owner_login] if owner_login else [],
            repos=[full_name] if full_name else [],
            published_at=created_at or pushed_at,
            fetched_at=fetched_at,
            topics=[],
            entities=[],
            keywords=keywords,
            source_metadata=SourceMetadata(
                source=SourceType.GITHUB,
                source_item_id=raw.source_item_id,
                source_url=canonical_url,
                fetched_at=fetched_at,
                connector_name=self.name,
                connector_version=self.connector_version,
                raw_payload_hash=payload_hash,
            ),
            signals=SignalBundle(
                common=CommonSignals(
                    freshness_days=freshness_days,
                    source_importance=0.7,
                ),
                github=GitHubSignals(
                    stars=_optional_int(raw.raw_payload.get("stargazers_count")),
                    forks=_optional_int(raw.raw_payload.get("forks_count")),
                    open_issues=_optional_int(raw.raw_payload.get("open_issues_count")),
                    last_pushed_at=pushed_at,
                ),
            ),
            source_payload_hash=payload_hash,
            content_fingerprint=content_fingerprint(full_name, description),
        )

    def build_query_urls(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[str]:
        effective_limit = limit if limit is not None else self.max_results
        query_terms = self.queries or ["AI agent"]
        return [
            self._build_query_url(query, since=since, per_page=effective_limit)
            for query in query_terms
        ]

    def _build_query_url(
        self,
        query: str,
        *,
        since: datetime | None,
        per_page: int,
    ) -> str:
        search_query = self._build_search_query(query, since=since)
        params = {
            "q": search_query,
            "sort": "updated",
            "order": "desc",
            "per_page": str(per_page),
        }
        return f"{GITHUB_SEARCH_API_URL}?{urllib.parse.urlencode(params)}"

    def _build_search_query(self, query: str, *, since: datetime | None) -> str:
        parts = [query]
        cutoff = self._cutoff_datetime(since)
        if cutoff is not None:
            parts.append(f"pushed:>={cutoff.date().isoformat()}")
        if self.min_stars is not None:
            parts.append(f"stars:>={int(self.min_stars)}")
        return " ".join(parts)

    def _fetch_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=self._request_headers())
        with urllib.request.urlopen(request, timeout=20) as response:
            data: bytes = response.read()
        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def _request_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _repo_to_raw(
        self,
        repo: dict[str, Any],
        *,
        fetched_at: datetime,
    ) -> RawSourceItem | None:
        if repo.get("archived") is True or repo.get("disabled") is True:
            return None
        stars = _optional_int(repo.get("stargazers_count")) or 0
        if self.min_stars is not None and stars < int(self.min_stars):
            return None
        full_name = repo.get("full_name")
        html_url = repo.get("html_url")
        if not isinstance(full_name, str) or not full_name:
            return None
        if not isinstance(html_url, str) or not html_url:
            return None
        canonical_url = canonicalize_github_url(html_url)
        description = repo.get("description")
        description_text = description if isinstance(description, str) else None
        payload: dict[str, Any] = {
            "id": repo.get("id"),
            "node_id": repo.get("node_id"),
            "full_name": full_name,
            "html_url": html_url,
            "description": description_text,
            "stargazers_count": repo.get("stargazers_count"),
            "forks_count": repo.get("forks_count"),
            "open_issues_count": repo.get("open_issues_count"),
            "pushed_at": repo.get("pushed_at"),
            "updated_at": repo.get("updated_at"),
            "created_at": repo.get("created_at"),
            "topics": repo.get("topics")
            if isinstance(repo.get("topics"), list)
            else [],
            "language": repo.get("language"),
            "archived": repo.get("archived"),
            "disabled": repo.get("disabled"),
            "license": repo.get("license"),
            "owner": repo.get("owner"),
        }
        source_item_id = full_name or str(repo.get("node_id") or "")
        return RawSourceItem(
            source=SourceType.GITHUB,
            source_item_id=source_item_id,
            raw_url=canonical_url,
            raw_title=full_name,
            raw_text=description_text,
            raw_payload=payload,
            fetched_at=fetched_at,
        )

    def _cutoff_datetime(self, since: datetime | None) -> datetime | None:
        if since is not None:
            return _ensure_timezone(since)
        if self.freshness_days is None:
            return None
        return datetime.now(timezone.utc) - timedelta(days=int(self.freshness_days))


def _get_config_value(config: Any, name: str, default: Any) -> Any:
    if isinstance(config, dict):
        return config.get(name, default)
    return getattr(config, name, default)


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return _ensure_timezone(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _owner_login(payload: dict[str, Any]) -> str | None:
    owner = payload.get("owner")
    if not isinstance(owner, dict):
        return None
    login = owner.get("login")
    if not isinstance(login, str) or not login:
        return None
    return login
