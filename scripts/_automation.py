from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from airi.config import load_app_config
from airi.delivery import EmailDelivery, preview_without_credentials
from airi.eval import RankingEvaluator
from airi.intelligence import (
    CrossSourceAnalyzer,
    DedupeEngine,
    EntityExtractor,
    NoveltyTracker,
    PaperRepoLinker,
    TopicExtractor,
    TrendEngine,
)
from airi.models import IntelligenceItem, SourceType
from airi.rank import ItemRanker, ItemScorer
from airi.report import (
    AlertsReportGenerator,
    EcosystemReportGenerator,
    WeeklyReportGenerator,
)
from airi.storage import StateStore, StoragePaths

FETCH_COMMANDS = {
    "arxiv": ["airi", "fetch", "arxiv", "--limit", "10"],
    "github": ["airi", "fetch", "github", "--limit", "10"],
    "hackernews": ["airi", "fetch", "hn", "--limit", "10"],
    "company_blogs": ["airi", "fetch", "company", "--limit", "10"],
    "openreview": ["airi", "fetch", "openreview", "--limit", "10"],
    "devpost": ["airi", "fetch", "devpost", "--limit", "10"],
}


def fetch_enabled_sources(*, dry_run: bool, source_ids: set[str] | None = None) -> None:
    if dry_run:
        print("Dry run: skipping external fetch.")
        return
    config = load_app_config()
    for source in config.sources.sources:
        if not source.enabled:
            continue
        if source_ids is not None and source.id not in source_ids:
            continue
        command = FETCH_COMMANDS.get(source.id)
        if command is None:
            continue
        print(f"Fetching source: {source.id}")
        subprocess.run(command, check=False)


def load_items(state: StateStore) -> list[IntelligenceItem]:
    return [
        IntelligenceItem.model_validate(record)
        for record in state.load_latest_items()
    ]


def process_items(*, update_seen: bool = False) -> list[IntelligenceItem]:
    config = load_app_config()
    paths = StoragePaths.default()
    state = StateStore(paths)
    items = load_items(state)
    items = TopicExtractor(config.topics).apply(items)
    items = EntityExtractor(config.watchlists).apply(items)
    items = DedupeEngine().dedupe(items).items
    NoveltyTracker(state).compute(items)
    if update_seen:
        NoveltyTracker(state).update_seen(items)
    ranked = ItemRanker(
        ItemScorer(config.scoring, config.profile, "intelligence"),
        force=True,
    ).score_and_rank(items)
    state.save_latest_items(item.model_dump(mode="json") for item in ranked)
    TrendEngine(state).update_timeseries(ranked)
    ranked = CrossSourceAnalyzer(config.scoring).apply_to_scores(ranked)
    state.save_latest_items(item.model_dump(mode="json") for item in ranked)
    return ranked


def generate_weekly_report() -> Path:
    config = load_app_config()
    paths = StoragePaths.default()
    state = StateStore(paths)
    items = load_items(state)
    trends = TrendEngine(state).analyze(items)
    correlations = CrossSourceAnalyzer(config.scoring).analyze(items)
    links = PaperRepoLinker().link(items)
    markdown = WeeklyReportGenerator(
        top=config.scoring.limits.max_report_items
    ).generate(items, trends, correlations, links)
    return write_report("weekly", markdown)


def generate_ecosystem_report() -> Path:
    config = load_app_config()
    paths = StoragePaths.default()
    state = StateStore(paths)
    items = load_items(state)
    correlations = CrossSourceAnalyzer(config.scoring).analyze(items)
    links = PaperRepoLinker().link(items)
    markdown = EcosystemReportGenerator(
        top=config.scoring.limits.max_report_items
    ).generate(items, correlations, links)
    return write_report("ecosystem", markdown)


def generate_alerts_report() -> Path:
    config = load_app_config()
    paths = StoragePaths.default()
    state = StateStore(paths)
    items = load_items(state)
    correlations = CrossSourceAnalyzer(config.scoring).analyze(items)
    markdown = AlertsReportGenerator(
        alert_threshold=config.scoring.thresholds.strong_signal
    ).generate(items, correlations)
    return write_report("alerts", markdown)


def write_report(report_type: str, markdown: str) -> Path:
    from datetime import datetime, timezone

    paths = StoragePaths.default()
    path = paths.reports_dir / report_type / f"{datetime.now(timezone.utc).date()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def maybe_email_report(path: Path, *, no_email: bool, dry_run: bool) -> None:
    if no_email:
        print("Email disabled by --no-email.")
        return
    body = path.read_text(encoding="utf-8")
    subject = f"AI Research Intelligence Report: {path.stem}"
    if dry_run:
        preview = preview_without_credentials(
            subject,
            body,
            StoragePaths.default().reports_dir / "email_preview",
        )
        print(f"Dry run email preview: {preview}")
        return
    EmailDelivery.from_env().send(subject, body)
    print("Email sent.")


def render_eval_report() -> Path:
    paths = StoragePaths.default()
    state = StateStore(paths)
    items = load_items(state)
    metrics, markdown = RankingEvaluator().evaluate_and_render(items)
    from datetime import datetime, timezone

    path = paths.reports_dir / "eval" / f"eval-{datetime.now(timezone.utc).date()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    for key in sorted(metrics):
        print(f"{key}: {metrics[key]:.3f}")
    return path


def ecosystem_source_ids() -> set[str]:
    return {
        SourceType.GITHUB.value,
        SourceType.HACKERNEWS.value,
        SourceType.COMPANY_BLOGS.value,
        SourceType.DEVPOST.value,
    }


def main_guard() -> None:
    if Path.cwd().name == "scripts":
        sys.path.insert(0, str(Path.cwd().parent))
