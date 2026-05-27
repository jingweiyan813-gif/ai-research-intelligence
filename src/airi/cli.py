from __future__ import annotations

import json
import platform
import sys
from typing import Optional

import typer

from airi import __version__
from airi.config import ConfigLoadError, load_app_config
from airi.connectors import (
    ArxivConnector,
    CompanyBlogsConnector,
    DevpostConnector,
    FakeConnector,
    GitHubConnector,
    HackerNewsConnector,
    OpenReviewConnector,
)
from airi.intelligence import (
    DedupeEngine,
    EntityExtractor,
    NoveltyTracker,
    TopicExtractor,
)
from airi.models import IntelligenceItem
from airi.pipeline import FetchPipeline
from airi.storage import StateStore, StoragePaths

app = typer.Typer(help="AI Research Intelligence CLI")
config_app = typer.Typer(help="Validate and inspect configuration files.")
storage_app = typer.Typer(help="Inspect and initialize local storage directories.")
fetch_app = typer.Typer(help="Run source fetch pipelines.")
intelligence_app = typer.Typer(help="Run local intelligence processing.")
app.add_typer(config_app, name="config")
app.add_typer(storage_app, name="storage")
app.add_typer(fetch_app, name="fetch")
app.add_typer(intelligence_app, name="intelligence")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


@app.command()
def doctor(
    config: Optional[str] = typer.Option(None, help="Optional path to a config file."),
) -> None:
    """Run a basic environment check."""
    typer.echo("Python: %s" % platform.python_version())
    typer.echo("Platform: %s" % platform.system())
    typer.echo("Path: %s" % sys.executable)
    if config:
        typer.echo("Config path: %s" % config)


@config_app.command("validate")
def validate_config() -> None:
    """Validate all default configuration files."""
    try:
        load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Configuration validation passed.")


@config_app.command("show")
def show_config() -> None:
    """Print a sanitized configuration summary."""
    try:
        config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(config.sanitized_summary(), ensure_ascii=False, indent=2))


@storage_app.command("doctor")
def storage_doctor() -> None:
    """Create public storage dirs and print storage paths."""
    paths = StoragePaths.default()
    paths.ensure_public_dirs()
    typer.echo("Storage directories:")
    typer.echo(f"  state:   {paths.state_dir} (public)")
    typer.echo(f"  reports: {paths.reports_dir} (public)")
    typer.echo(f"  sample:  {paths.sample_dir} (public)")
    typer.echo(f"  cache:   {paths.cache_dir} (private, gitignored)")
    typer.echo(f"  raw:     {paths.raw_dir} (private, gitignored)")


@storage_app.command("init")
def storage_init(
    private: bool = typer.Option(
        False,
        "--private",
        help="Also create private gitignored cache/raw directories.",
    ),
) -> None:
    """Initialize storage directories."""
    paths = StoragePaths.default()
    paths.ensure_public_dirs()
    typer.echo(
        "Created public storage directories: data/state, data/reports, data/sample"
    )
    if private:
        paths.ensure_private_dirs()
        typer.echo("Created private storage directories: data/cache, data/raw")


@fetch_app.command("fake")
def fetch_fake(
    limit: int = typer.Option(3, "--limit", min=0, help="Number of fake items."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
    strict: bool = typer.Option(False, "--strict", help="Fail on connector errors."),
) -> None:
    """Run the deterministic fake connector smoke pipeline."""
    paths = StoragePaths.default()
    pipeline = FetchPipeline(
        connectors=[FakeConnector(item_count=limit)],
        state_store=StateStore(paths),
    )
    try:
        result = pipeline.run(limit_per_source=limit, strict=strict, save=not no_save)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Total items: {result.total_items}")
    typer.echo(f"Total errors: {result.total_errors}")
    for connector_result in result.connector_results:
        typer.echo(
            "Source "
            f"{connector_result.source.value}: "
            f"raw={connector_result.raw_count}, "
            f"normalized={connector_result.normalized_count}, "
            f"errors={len(connector_result.errors)}"
        )


@fetch_app.command("arxiv")
def fetch_arxiv(
    limit: int | None = typer.Option(None, "--limit", min=1, help="Max arXiv items."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
    strict: bool = typer.Option(False, "--strict", help="Fail on connector errors."),
    days: int | None = typer.Option(None, "--days", min=1, help="Freshness window."),
) -> None:
    """Run the metadata-only arXiv fetch pipeline."""
    try:
        app_config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    arxiv_config = next(
        (
            source_config
            for source_config in app_config.sources.sources
            if source_config.id == "arxiv"
        ),
        None,
    )
    if arxiv_config is None:
        typer.echo("arxiv source config not found", err=True)
        raise typer.Exit(code=1)
    if days is not None:
        arxiv_config = arxiv_config.model_copy(update={"freshness_days": days})

    paths = StoragePaths.default()
    pipeline = FetchPipeline(
        connectors=[ArxivConnector(arxiv_config)],
        state_store=StateStore(paths),
    )
    try:
        result = pipeline.run(limit_per_source=limit, strict=strict, save=not no_save)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Total items: {result.total_items}")
    typer.echo(f"Total errors: {result.total_errors}")
    for connector_result in result.connector_results:
        typer.echo(
            "Source "
            f"{connector_result.source.value}: "
            f"raw={connector_result.raw_count}, "
            f"normalized={connector_result.normalized_count}, "
            f"errors={len(connector_result.errors)}"
        )


@fetch_app.command("github")
def fetch_github(
    limit: int | None = typer.Option(None, "--limit", min=1, help="Max repos."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
    strict: bool = typer.Option(False, "--strict", help="Fail on connector errors."),
    days: int | None = typer.Option(None, "--days", min=1, help="Freshness window."),
) -> None:
    """Run the metadata-first GitHub repository fetch pipeline."""
    try:
        app_config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    github_config = next(
        (
            source_config
            for source_config in app_config.sources.sources
            if source_config.id == "github"
        ),
        None,
    )
    if github_config is None:
        typer.echo("github source config not found", err=True)
        raise typer.Exit(code=1)
    if days is not None:
        github_config = github_config.model_copy(update={"freshness_days": days})

    paths = StoragePaths.default()
    pipeline = FetchPipeline(
        connectors=[GitHubConnector(github_config)],
        state_store=StateStore(paths),
    )
    try:
        result = pipeline.run(limit_per_source=limit, strict=strict, save=not no_save)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Total items: {result.total_items}")
    typer.echo(f"Total errors: {result.total_errors}")
    for connector_result in result.connector_results:
        typer.echo(
            "Source "
            f"{connector_result.source.value}: "
            f"raw={connector_result.raw_count}, "
            f"normalized={connector_result.normalized_count}, "
            f"errors={len(connector_result.errors)}"
        )


@fetch_app.command("hn")
def fetch_hn(
    limit: int | None = typer.Option(None, "--limit", min=1, help="Max HN items."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
    strict: bool = typer.Option(False, "--strict", help="Fail on connector errors."),
    days: int | None = typer.Option(None, "--days", min=1, help="Freshness window."),
) -> None:
    """Run the metadata-only Hacker News fetch pipeline."""
    _run_configured_single_source(
        source_id="hackernews",
        connector_factory=HackerNewsConnector,
        limit=limit,
        no_save=no_save,
        strict=strict,
        days=days,
    )


@fetch_app.command("company")
def fetch_company(
    limit: int | None = typer.Option(None, "--limit", min=1, help="Max entries."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
    strict: bool = typer.Option(False, "--strict", help="Fail on connector errors."),
    days: int | None = typer.Option(None, "--days", min=1, help="Freshness window."),
) -> None:
    """Run the metadata-only company RSS/blog fetch pipeline."""
    _run_configured_single_source(
        source_id="company_blogs",
        connector_factory=CompanyBlogsConnector,
        limit=limit,
        no_save=no_save,
        strict=strict,
        days=days,
    )


@fetch_app.command("openreview")
def fetch_openreview(
    limit: int | None = typer.Option(None, "--limit", min=1, help="Max notes."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
    strict: bool = typer.Option(False, "--strict", help="Fail on connector errors."),
    days: int | None = typer.Option(None, "--days", min=1, help="Freshness window."),
) -> None:
    """Run the metadata-only OpenReview fetch pipeline."""
    _run_configured_single_source(
        source_id="openreview",
        connector_factory=OpenReviewConnector,
        limit=limit,
        no_save=no_save,
        strict=strict,
        days=days,
    )


@fetch_app.command("devpost")
def fetch_devpost(
    limit: int | None = typer.Option(None, "--limit", min=1, help="Max hackathons."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
    strict: bool = typer.Option(False, "--strict", help="Fail on connector errors."),
    days: int | None = typer.Option(None, "--days", min=1, help="Days ahead."),
) -> None:
    """Run the metadata-only Devpost fetch pipeline."""
    try:
        app_config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    devpost_config = next(
        (
            candidate
            for candidate in app_config.sources.sources
            if candidate.id == "devpost"
        ),
        None,
    )
    if devpost_config is None:
        typer.echo("devpost source config not found", err=True)
        raise typer.Exit(code=1)
    if days is not None:
        devpost_config = devpost_config.model_copy(update={"days_ahead": days})

    paths = StoragePaths.default()
    pipeline = FetchPipeline(
        connectors=[DevpostConnector(devpost_config)],
        state_store=StateStore(paths),
    )
    try:
        result = pipeline.run(limit_per_source=limit, strict=strict, save=not no_save)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Total items: {result.total_items}")
    typer.echo(f"Total errors: {result.total_errors}")
    for connector_result in result.connector_results:
        typer.echo(
            "Source "
            f"{connector_result.source.value}: "
            f"raw={connector_result.raw_count}, "
            f"normalized={connector_result.normalized_count}, "
            f"errors={len(connector_result.errors)}"
        )


def _run_configured_single_source(
    *,
    source_id: str,
    connector_factory: object,
    limit: int | None,
    no_save: bool,
    strict: bool,
    days: int | None,
) -> None:
    try:
        app_config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    source_config = next(
        (
            candidate
            for candidate in app_config.sources.sources
            if candidate.id == source_id
        ),
        None,
    )
    if source_config is None:
        typer.echo(f"{source_id} source config not found", err=True)
        raise typer.Exit(code=1)
    if days is not None:
        source_config = source_config.model_copy(update={"freshness_days": days})

    connector = connector_factory(source_config)  # type: ignore[operator]
    paths = StoragePaths.default()
    pipeline = FetchPipeline(connectors=[connector], state_store=StateStore(paths))
    try:
        result = pipeline.run(limit_per_source=limit, strict=strict, save=not no_save)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Total items: {result.total_items}")
    typer.echo(f"Total errors: {result.total_errors}")
    for connector_result in result.connector_results:
        typer.echo(
            "Source "
            f"{connector_result.source.value}: "
            f"raw={connector_result.raw_count}, "
            f"normalized={connector_result.normalized_count}, "
            f"errors={len(connector_result.errors)}"
        )


@intelligence_app.command("dedupe")
def intelligence_dedupe(
    no_save: bool = typer.Option(False, "--no-save", help="Do not write latest_items."),
    limit: int | None = typer.Option(None, "--limit", min=1, help="Limit input items."),
) -> None:
    """Deduplicate latest fetched items."""
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store, limit=limit)
    result = DedupeEngine().dedupe(items)
    if not no_save:
        state_store.save_latest_items(
            item.model_dump(mode="json") for item in result.items
        )
    typer.echo(f"Removed duplicates: {result.removed_count}")
    typer.echo(f"Duplicate groups: {len(result.duplicate_groups)}")


@intelligence_app.command("novelty")
def intelligence_novelty(
    update_seen: bool = typer.Option(
        False,
        "--update-seen",
        help="Update seen_items.json after computing novelty.",
    ),
    limit: int | None = typer.Option(None, "--limit", min=1, help="Limit input items."),
) -> None:
    """Compute novelty for latest fetched items."""
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store, limit=limit)
    tracker = NoveltyTracker(state_store)
    results = tracker.compute(items)
    new_count = sum(not result.seen_before for result in results.values())
    seen_count = len(results) - new_count
    if update_seen:
        tracker.update_seen(items)
    typer.echo(f"Items checked: {len(items)}")
    typer.echo(f"New items: {new_count}")
    typer.echo(f"Seen items: {seen_count}")
    if update_seen:
        typer.echo("Seen state updated: yes")


@intelligence_app.command("extract")
def intelligence_extract(
    no_save: bool = typer.Option(False, "--no-save", help="Do not write latest_items."),
    limit: int | None = typer.Option(None, "--limit", min=1, help="Limit input items."),
) -> None:
    """Apply rule-based topic and entity extraction to latest items."""
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store, limit=limit)
    try:
        app_config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    extracted = TopicExtractor(app_config.topics).apply(items)
    extracted = EntityExtractor(app_config.watchlists).apply(extracted)
    updated_count = sum(
        before.topics != after.topics or before.entities != after.entities
        for before, after in zip(items, extracted, strict=True)
    )
    if not no_save:
        state_store.save_latest_items(
            item.model_dump(mode="json") for item in extracted
        )
    typer.echo(f"Items processed: {len(items)}")
    typer.echo(f"Items updated: {updated_count}")


def _load_latest_intelligence_items(
    state_store: StateStore,
    *,
    limit: int | None = None,
) -> list[IntelligenceItem]:
    records = state_store.load_latest_items()
    if limit is not None:
        records = records[:limit]
    return [IntelligenceItem.model_validate(record) for record in records]
