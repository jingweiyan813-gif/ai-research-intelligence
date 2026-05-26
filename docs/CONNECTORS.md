# CONNECTORS

Step 6 defines the connector framework only. It does not implement real external connectors and does not call external APIs.

## Connector Contract

Every connector should subclass `BaseConnector` and provide:

- `name`: stable connector name, for example `arxiv` or `github` in future steps.
- `source`: `SourceType` enum value.
- `connector_version`: connector implementation version, defaulting to `v1`.
- `fetch_raw(since=None, limit=None)`: returns `list[RawSourceItem]`.
- `normalize(raw)`: converts one `RawSourceItem` into one `IntelligenceItem`.

`fetch_and_normalize()` is implemented by the base class and should usually not be reimplemented. It records:

- source
- raw count
- normalized count
- errors
- started timestamp
- completed timestamp

## Error Isolation

Connector-level `fetch_raw()` errors are captured in `ConnectorResult.errors` and return zero items. Item-level normalization errors are also captured, but other raw items continue to normalize.

The fetch pipeline continues after connector errors by default. Strict mode raises a `RuntimeError` when any connector reports errors.

## Source Health

When `FetchPipeline.run(save=True)` is used, state is written through `StateStore`:

- `data/state/latest_items.jsonl`
- `data/state/source_health.json`
- `data/state/last_run.json`

`source_health.json` includes raw count, normalized count, error count, errors, and timestamps for each source.

## FakeConnector

`FakeConnector` is deterministic and exists only for tests and smoke checks:

```bash
airi fetch fake
airi fetch fake --limit 5 --no-save
```

It must not be treated as a real source connector. Concrete connectors for arXiv, GitHub, Hacker News, OpenReview, RSS/company blogs, and Devpost will be added later.

## arXiv Connector

`ArxivConnector` is the first real connector and is implemented in `src/airi/connectors/arxiv.py`.

Scope:

- Uses `https://export.arxiv.org/api/query`.
- Fetches metadata only.
- Does not download PDFs.
- Does not call LLMs.
- Does not score, dedupe, or rank papers.

Config fields are read from the arXiv source entry in `configs/sources.yml`:

- `queries`: keyword searches converted to `all:"..."` arXiv queries.
- `categories`: category searches converted to `cat:<category>` queries.
- `max_results`: default request/result cap.
- `freshness_days`: default recency filter.
- `enabled`: disables the connector when false.

Normalization behavior:

- arXiv PDF and abs URLs canonicalize to `https://arxiv.org/abs/<id>`.
- `RawSourceItem.raw_payload` keeps id, title, summary, authors, categories, published, updated, links, and primary category.
- `IntelligenceItem` uses `ItemType.PAPER`, `SourceType.ARXIV`, `SourceMetadata`, `SignalBundle`, `PaperSignals`, `source_payload_hash`, and `content_fingerprint`.

CLI smoke command:

```bash
airi fetch arxiv --limit 2 --no-save
```

Concrete connectors for GitHub, Hacker News, OpenReview, RSS/company blogs, and Devpost remain out of scope for this step.

## GitHub Connector

`GitHubConnector` is implemented in `src/airi/connectors/github.py` and uses the GitHub Search Repositories API.

Scope:

- Uses `https://api.github.com/search/repositories`.
- Fetches public repository metadata only.
- Does not clone repositories.
- Does not fetch file trees.
- Does not download repository archives.
- Does not call GitHub contents APIs.
- Does not score, dedupe, rank, or summarize repositories.

Config fields are read from the GitHub source entry in `configs/sources.yml`:

- `queries`: search terms.
- `min_stars`: lower bound added as `stars:>=N`.
- `freshness_days`: lower bound added as `pushed:>=YYYY-MM-DD`.
- `max_results`: default request/result cap.
- `enabled`: disables the connector when false.

Authentication:

- If `GH_TOKEN` or `GITHUB_TOKEN` is set, requests include `Authorization: Bearer <token>`.
- If no token exists, unauthenticated requests are still supported with lower rate limits.

Normalization behavior:

- GitHub repo URLs canonicalize to `https://github.com/<owner>/<repo>`.
- Archived, disabled, below-star-threshold, and stale repositories are filtered out.
- `RawSourceItem.raw_payload` keeps id, node id, full name, URL, description, stars, forks, open issues, pushed/updated/created timestamps, topics, language, archived/disabled flags, license, and owner.
- `IntelligenceItem` uses `ItemType.REPO`, `SourceType.GITHUB`, `SourceMetadata`, `SignalBundle`, `GitHubSignals`, `source_payload_hash`, and `content_fingerprint`.

CLI smoke command:

```bash
airi fetch github --limit 2 --no-save
```

Concrete connectors for Hacker News, OpenReview, RSS/company blogs, and Devpost remain out of scope for this step.

## Hacker News Connector

`HackerNewsConnector` is implemented in `src/airi/connectors/hackernews.py` and uses the official Hacker News Firebase API.

Scope:

- Reads `topstories.json` and `newstories.json`.
- Reads item metadata from `item/<id>.json`.
- Does not fetch comments.
- Does not scrape linked pages.
- Does not summarize or classify with LLMs.

Config fields from `configs/sources.yml`:

- `keywords`: matched against story title and URL.
- `min_score`: lower score bound when a score exists.
- `freshness_days`: recency filter based on item time.
- `max_results`: maximum item fetches/results.
- `enabled`: disables the connector when false.

Normalization behavior:

- Stories become `ItemType.DISCUSSION` items.
- `score` and `descendants` map to `CommunitySignals`.
- Stories without external URLs use the Hacker News item URL only when they match configured keywords.
- Deleted/dead stories, non-story items, missing titles, stale items, and low-score items are skipped.

## Company RSS / Blog Connector

`RSSConnector` is the generic RSS/Atom parser in `src/airi/connectors/rss.py`. `CompanyBlogsConnector` wraps configured official company/lab feeds in `src/airi/connectors/company_blogs.py`.

Scope:

- Reads public RSS/Atom feed metadata.
- Does not scrape full article pages.
- Does not call LLMs.
- Does not score, dedupe, or rank entries.

Config fields from `configs/sources.yml` company_blogs source:

- `feeds`: list of `{name, url}` feed definitions.
- `keywords`: matched against title and summary.
- `freshness_days`: recency filter based on published/updated time.
- `max_results`: result cap.
- `enabled`: disables the connector when false.

Normalization behavior:

- Entries become `ItemType.COMPANY_UPDATE` items.
- Feed/company name maps to `CompanySignals.company_name`.
- `CompanySignals.is_official_announcement` is true.
- Bad feeds are captured as connector errors without failing all feeds.
