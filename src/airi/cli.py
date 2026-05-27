from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
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
from airi.delivery import EmailConfigError, EmailDelivery, preview_without_credentials
from airi.eval import DEFAULT_GOLD_PATH, RankingEvaluator
from airi.intelligence import (
    CrossSourceAnalyzer,
    DedupeEngine,
    EntityExtractor,
    NoveltyTracker,
    PaperRepoLinker,
    TopicExtractor,
    TrendEngine,
)
from airi.models import IntelligenceItem
from airi.pipeline import FetchPipeline
from airi.rank import ItemRanker, ItemScorer, explain_score, summarize_top_items
from airi.report import (
    AlertsReportGenerator,
    EcosystemReportGenerator,
    WeeklyReportGenerator,
)
from airi.storage import StateStore, StoragePaths

app = typer.Typer(help="AI Research Intelligence CLI")
config_app = typer.Typer(help="Validate and inspect configuration files.")
storage_app = typer.Typer(help="Inspect and initialize local storage directories.")
fetch_app = typer.Typer(help="Run source fetch pipelines.")
intelligence_app = typer.Typer(help="Run local intelligence processing.")
rank_app = typer.Typer(help="Score and rank latest items.")
link_app = typer.Typer(help="Link related intelligence items.")
report_app = typer.Typer(help="Generate markdown intelligence reports.")
email_app = typer.Typer(help="Preview and send report emails.")
eval_app = typer.Typer(help="Evaluate ranking and report quality.")
app.add_typer(config_app, name="config")
app.add_typer(storage_app, name="storage")
app.add_typer(fetch_app, name="fetch")
app.add_typer(intelligence_app, name="intelligence")
app.add_typer(rank_app, name="rank")
app.add_typer(link_app, name="link")
app.add_typer(report_app, name="report")
app.add_typer(email_app, name="email")
app.add_typer(eval_app, name="eval")


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


@rank_app.callback(invoke_without_command=True)
def rank_items(
    ctx: typer.Context,
    top: int | None = typer.Option(None, "--top", min=1, help="Number of items."),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Ranking profile: item_baseline, intelligence, or personal.",
    ),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write latest_items."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-score existing scored items.",
    ),
    min_score: float | None = typer.Option(None, "--min-score", min=0.0, max=1.0),
) -> None:
    """Score and rank latest items."""
    if ctx.invoked_subcommand is not None:
        return
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store)
    try:
        app_config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    effective_top = top or app_config.scoring.limits.max_report_items
    try:
        scorer = ItemScorer(app_config.scoring, app_config.profile, profile)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    ranked = ItemRanker(scorer, force=force).score_and_rank(items)
    if min_score is not None:
        ranked = [
            item
            for item in ranked
            if item.scores and item.scores.final_score >= min_score
        ]
    shown = ranked[:effective_top]
    typer.echo(summarize_top_items(shown, top=effective_top))
    if not no_save:
        state_store.save_latest_items(item.model_dump(mode="json") for item in ranked)


@rank_app.command("explain")
def rank_explain(item_id: str) -> None:
    """Explain score breakdown for one item."""
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store)
    for item in items:
        if item.id == item_id:
            typer.echo(explain_score(item))
            return
    typer.echo(f"Item not found: {item_id}", err=True)
    raise typer.Exit(code=1)


@app.command("trends")
def trends_command(
    window_days: int = typer.Option(30, "--window-days", min=1),
    update_timeseries: bool = typer.Option(
        False,
        "--update-timeseries",
        help="Update topic_timeseries.json with current topic counts.",
    ),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write state files."),
) -> None:
    """Analyze deterministic topic trends from latest items."""
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store)
    engine = TrendEngine(state_store)
    result = engine.analyze(items, window_days=window_days)
    typer.echo(f"Analyzed items: {result.analyzed_item_count}")
    if not result.trends:
        typer.echo("No topic trends found.")
    for trend in result.trends:
        typer.echo(
            f"{trend.topic}: {trend.trend_type.value} "
            f"items={trend.item_count} sources={trend.source_count} "
            f"growth={trend.growth_rate:.2f} momentum={trend.momentum_score:.2f}"
        )
    if result.claims:
        typer.echo("Claims:")
        for claim in result.claims:
            typer.echo(
                f"- {claim.claim} confidence={claim.confidence:.2f} "
                f"evidence={len(claim.evidence_refs)}"
            )
    if update_timeseries and not no_save:
        engine.update_timeseries(items)
        typer.echo("Topic timeseries updated: yes")
    elif update_timeseries:
        typer.echo("Topic timeseries updated: no (--no-save)")


@app.command("correlate")
def correlate_command(
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Apply cross-source correlation to existing item scores.",
    ),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write latest_items."),
) -> None:
    """Analyze deterministic cross-source topic signals."""
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store)
    scoring_config = None
    if apply:
        try:
            scoring_config = load_app_config().scoring
        except ConfigLoadError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
    analyzer = CrossSourceAnalyzer(scoring_config)
    signals = analyzer.analyze(items)
    typer.echo(f"Cross-source signals: {len(signals)}")
    for signal in signals:
        typer.echo(
            f"{signal.topic}: strength={signal.strength:.2f} "
            f"sources={','.join(signal.sources)} items={len(signal.item_ids)}"
        )
    if apply:
        updated = analyzer.apply_to_scores(items)
        if not no_save:
            state_store.save_latest_items(
                item.model_dump(mode="json") for item in updated
            )
            typer.echo("Scores updated: yes")
        else:
            typer.echo("Scores updated: no (--no-save)")


@link_app.command("paper-repos")
def link_paper_repos() -> None:
    """Print deterministic paper-repository link candidates."""
    state_store = StateStore(StoragePaths.default())
    items = _load_latest_intelligence_items(state_store)
    links = PaperRepoLinker().link(items)
    typer.echo(f"Paper-repo links: {len(links)}")
    for link in links:
        terms = ", ".join(link.matched_terms)
        typer.echo(
            f"{link.paper_item_id} -> {link.repo_item_id} "
            f"confidence={link.confidence:.2f} reason={link.reason} terms={terms}"
        )


@report_app.command("weekly")
def report_weekly(
    top: int | None = typer.Option(None, "--top", min=1),
    output: Path | None = typer.Option(None, "--output"),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Ranking profile: item_baseline, intelligence, or personal.",
    ),
) -> None:
    """Generate a deterministic weekly markdown report."""
    paths = StoragePaths.default()
    state_store = StateStore(paths)
    try:
        app_config = load_app_config()
        ranked = _scored_ranked_items(
            state_store,
            app_config.scoring,
            app_config.profile,
            profile=profile,
        )
    except (ConfigLoadError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    effective_top = top or app_config.scoring.limits.max_report_items
    trend_result = TrendEngine(state_store).analyze(ranked)
    correlations = CrossSourceAnalyzer(app_config.scoring).analyze(ranked)
    links = PaperRepoLinker().link(ranked)
    markdown = WeeklyReportGenerator(top=effective_top).generate(
        ranked,
        trend_result,
        correlations,
        links,
    )
    report_path = _write_report(paths, "weekly", markdown, output)
    typer.echo(f"Report written: {report_path}")


@report_app.command("ecosystem")
def report_ecosystem(
    top: int | None = typer.Option(None, "--top", min=1),
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    """Generate a deterministic ecosystem markdown report."""
    paths = StoragePaths.default()
    state_store = StateStore(paths)
    try:
        app_config = load_app_config()
        ranked = _scored_ranked_items(
            state_store,
            app_config.scoring,
            app_config.profile,
        )
    except (ConfigLoadError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    effective_top = top or app_config.scoring.limits.max_report_items
    correlations = CrossSourceAnalyzer(app_config.scoring).analyze(ranked)
    links = PaperRepoLinker().link(ranked)
    markdown = EcosystemReportGenerator(top=effective_top).generate(
        ranked,
        correlations,
        links,
    )
    report_path = _write_report(paths, "ecosystem", markdown, output)
    typer.echo(f"Report written: {report_path}")


@report_app.command("alerts")
def report_alerts(
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    """Generate deterministic markdown alerts."""
    paths = StoragePaths.default()
    state_store = StateStore(paths)
    try:
        app_config = load_app_config()
        ranked = _scored_ranked_items(
            state_store,
            app_config.scoring,
            app_config.profile,
        )
    except (ConfigLoadError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    correlations = CrossSourceAnalyzer(app_config.scoring).analyze(ranked)
    markdown = AlertsReportGenerator(
        alert_threshold=app_config.scoring.thresholds.strong_signal,
    ).generate(ranked, correlations)
    report_path = _write_report(paths, "alerts", markdown, output)
    typer.echo(f"Report written: {report_path}")


def _scored_ranked_items(
    state_store: StateStore,
    scoring_config: object,
    profile_config: object,
    *,
    profile: str | None = None,
) -> list[IntelligenceItem]:
    items = _load_latest_intelligence_items(state_store)
    scorer = ItemScorer(scoring_config, profile_config, profile)
    return ItemRanker(scorer, force=profile is not None).score_and_rank(items)


def _write_report(
    paths: StoragePaths,
    report_type: str,
    markdown: str,
    output: Path | None,
) -> Path:
    date = datetime.now(timezone.utc).date().isoformat()
    path = output or paths.reports_dir / report_type / f"{date}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


@email_app.command("preview")
def email_preview(report_path: Path) -> None:
    """Write an email preview file for a markdown report."""
    paths = StoragePaths.default()
    body = _read_report(report_path)
    subject = _default_email_subject(report_path)
    output = preview_without_credentials(
        subject,
        body,
        paths.reports_dir / "email_preview",
    )
    typer.echo(f"Email preview written: {output}")


@email_app.command("send")
def email_send(
    report_path: Path,
    subject: str | None = typer.Option(None, "--subject"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without sending."),
) -> None:
    """Send a markdown report by plain text email."""
    paths = StoragePaths.default()
    body = _read_report(report_path)
    resolved_subject = subject or _default_email_subject(report_path)
    if dry_run:
        output = preview_without_credentials(
            resolved_subject,
            body,
            paths.reports_dir / "email_preview",
        )
        typer.echo(f"Dry run email preview written: {output}")
        return
    try:
        EmailDelivery.from_env().send(resolved_subject, body)
    except EmailConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Email sent.")


@eval_app.command("ranking")
def eval_ranking(
    gold: Path = typer.Option(DEFAULT_GOLD_PATH, "--gold"),
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    """Evaluate ranked latest_items.jsonl with lightweight metrics."""
    paths = StoragePaths.default()
    state_store = StateStore(paths)
    items = _load_latest_intelligence_items(state_store)
    evaluator = RankingEvaluator(gold)
    metrics, markdown = evaluator.evaluate_and_render(items)
    report_path = output or paths.reports_dir / "eval" / _dated_filename("eval")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    typer.echo(f"Eval report written: {report_path}")
    for key in sorted(metrics):
        typer.echo(f"{key}: {metrics[key]:.3f}")


def _read_report(report_path: Path) -> str:
    try:
        return report_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"Report not found: {report_path}") from exc


def _default_email_subject(report_path: Path) -> str:
    return f"AI Research Intelligence Report: {report_path.stem}"


def _dated_filename(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).date().isoformat()}.md"
