from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from typer.testing import CliRunner

from airi.cli import app
from airi.config.schema import SourceConfig
from airi.connectors import BaseConnector
from airi.models import IntelligenceItem, RawSourceItem, SourceType
from airi.storage import StateStore, StoragePaths
from tests.factories import make_item

runner = CliRunner()


class FixedConnector(BaseConnector):
    name = "fixed"
    connector_version = "v1"

    def __init__(
        self,
        source: SourceType,
        *,
        count: int = 1,
        fail_fetch: bool = False,
    ) -> None:
        self.source = source
        self.count = count
        self.fail_fetch = fail_fetch

    def fetch_raw(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[RawSourceItem]:
        if self.fail_fetch:
            raise RuntimeError("boom")
        count = min(self.count, limit or self.count)
        return [
            RawSourceItem(
                source=self.source,
                source_item_id=f"{self.source.value}-{index}",
                raw_url=f"https://example.com/{self.source.value}/{index}",
                raw_title=f"{self.source.value} item {index}",
                raw_payload={"index": index},
                fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
            for index in range(count)
        ]

    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        return make_item(
            item_id=f"{raw.source.value}-{raw.source_item_id}",
            source=raw.source,
            title=raw.raw_title,
            url=raw.raw_url,
            source_item_id=raw.source_item_id,
        )


def test_fetch_all_aggregates_multiple_enabled_sources(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _patch_config_and_connectors(monkeypatch)
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["fetch", "all", "--limit-per-source", "2"])
        state = StateStore(StoragePaths.default())

        assert result.exit_code == 0
        assert "Total items: 4" in result.output
        assert "Source arxiv: raw=2, normalized=2, errors=0" in result.output
        assert "Source github: raw=2, normalized=2, errors=0" in result.output
        assert len(state.load_latest_items()) == 4
        assert set(state.load_source_health()) == {"arxiv", "github"}


def test_fetch_all_no_save_does_not_write(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _patch_config_and_connectors(monkeypatch)
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["fetch", "all", "--limit-per-source", "1", "--no-save"],
        )
        state = StateStore(StoragePaths.default())

        assert result.exit_code == 0
        assert "Total items: 2" in result.output
        assert state.load_latest_items() == []


def test_fetch_all_skips_disabled_sources(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _patch_config_and_connectors(monkeypatch, include_openreview=True)
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["fetch", "all", "--limit-per-source", "1"])

        assert result.exit_code == 0
        assert "Source openreview" not in result.output


def test_fetch_all_non_strict_continues_on_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _patch_config_and_connectors(monkeypatch, fail_github=True)
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["fetch", "all", "--limit-per-source", "1"])
        state = StateStore(StoragePaths.default())

        assert result.exit_code == 0
        assert "Total items: 1" in result.output
        assert "Total errors: 1" in result.output
        assert len(state.load_latest_items()) == 1


def test_fetch_all_strict_fails_on_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _patch_config_and_connectors(monkeypatch, fail_github=True)
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["fetch", "all", "--strict"])

        assert result.exit_code == 1
        assert "Connector fixed failed" in result.output


def _patch_config_and_connectors(
    monkeypatch,  # type: ignore[no-untyped-def]
    *,
    include_openreview: bool = False,
    fail_github: bool = False,
) -> None:
    import airi.cli as cli_module

    sources = [
        SourceConfig(id="arxiv", name="arXiv", enabled=True, type="paper"),
        SourceConfig(id="github", name="GitHub", enabled=True, type="repo"),
        SourceConfig(
            id="openreview",
            name="OpenReview",
            enabled=include_openreview and False,
            type="paper",
        ),
    ]
    monkeypatch.setattr(
        cli_module,
        "load_app_config",
        lambda: SimpleNamespace(sources=SimpleNamespace(sources=sources)),
    )
    monkeypatch.setattr(
        cli_module,
        "ArxivConnector",
        lambda config: FixedConnector(SourceType.ARXIV, count=3),
    )
    monkeypatch.setattr(
        cli_module,
        "GitHubConnector",
        lambda config: FixedConnector(
            SourceType.GITHUB,
            count=3,
            fail_fetch=fail_github,
        ),
    )
    monkeypatch.setattr(
        cli_module,
        "OpenReviewConnector",
        lambda config: FixedConnector(SourceType.OPENREVIEW, count=3),
    )
