# ARCHITECTURE

AIRI 的长期架构路线是：

`Source -> Normalize -> Dedupe -> Enrich -> Score -> Trend -> Report -> Email`

当前仓库处于 Step 2：配置系统。这个阶段只建立配置加载、结构校验和 CLI 检查能力，不实现任何真实连接器、评分、LLM、报告、邮件发送、数据库或仪表盘。

## Config Layer

配置层负责在流水线执行前定义系统边界：

- `sources.yml` 定义公开来源及默认启用状态。
- `topics.yml` 定义主要研究主题和负面主题。
- `scoring.yml` 定义未来评分所需的权重、阈值和数量限制。
- `profile.example.yml`、`email.example.yml`、`watchlists.example.yml` 提供可复制的本地配置模板。
- `profile.local.yml`、`email.local.yml`、`watchlists.local.yml` 是可选本地覆盖文件，不属于公开配置。

配置层的职责是“加载与验证”，不是“执行业务逻辑”。因此它不会抓取外部数据、调用 API、计算排名、发送邮件或写入数据库。

## Deterministic Loading

`airi.config.loader` 以固定文件名从 `configs/` 加载 YAML，并用 Pydantic schema 验证。可选本地覆盖文件只在存在时使用；不存在时自动回退到 `.example.yml`，因此本地开发和 CI 都能得到确定性行为。

## Data Contract Layer

Step 3 introduces the internal model layer under `src/airi/models/`. This layer defines the contracts that later connectors, normalizers, scorers, trend detectors, and report generators must exchange.

Design goals:

- **Traceability**：`IntelligenceItem` embeds `SourceMetadata`, so every normalized item keeps the original source, URL, connector name, connector version, fetch timestamp, and raw payload hash.
- **Evidence-grounded reporting**：`EvidenceRef` lets future `TrendClaim` and report sections point back to specific evidence items instead of making unsupported claims.
- **Explainable ranking**：`ScoreBundle` stores dimension-level scores, while `ScoreBreakdown` records human-readable reasons and related evidence item IDs.
- **Extraction auditability**：`ExtractionMetadata` records extraction method, extractor name, extractor version, timestamp, and optional confidence for topics/entities/keywords.
- **Modular source signals**：`SignalBundle` separates common, paper, GitHub, community, hackathon, and company signals so new source families can be added without changing every item contract.

This layer deliberately does not implement fetching, normalization algorithms, ranking logic, LLM calls, persistence, email, or dashboard behavior. It only defines validated data shapes.

## Storage Layer

Step 4 introduces a lightweight JSON/JSONL storage layer under `src/airi/storage/`. It is designed for personal use and GitHub Actions without requiring SQLite, Postgres, a vector database, or any server process.

Storage responsibilities:

- `StoragePaths` defines public and private data directories.
- `JSONStore` reads and writes pretty JSON with atomic replace to reduce the chance of corrupted state files.
- `JSONLStore` reads, writes, appends, and iterates JSONL records for item lists.
- `StateStore` wraps public state files such as `seen_items.json`, `topic_timeseries.json`, `source_health.json`, `last_run.json`, and `latest_items.jsonl`.
- `CacheStore` wraps private cache files under `data/cache/<namespace>/<safe_key>.json` and sanitizes keys to prevent path traversal.

Public directories are `data/state`, `data/reports`, and `data/sample`. Private/gitignored directories are `data/cache` and `data/raw`. The storage interfaces are intentionally small so they can later be migrated to SQLite or another backend without changing higher-level pipeline contracts.

This layer does not fetch external data, call APIs, score items, detect trends, call LLMs, send email, or power a dashboard.

## Normalization Layer

Step 5 introduces reusable normalization utilities under `src/airi/normalize/`. Future connectors should call this layer instead of implementing ad hoc cleanup inside each source adapter.

Responsibilities:

- `text.py` normalizes whitespace, line structure, matching text, and compact snippets.
- `url.py` strips tracking parameters and canonicalizes generic, arXiv, and GitHub URLs.
- `fingerprint.py` creates deterministic SHA-256 hashes for content, payloads, and stable multi-part keys.
- `slug.py` creates safe slugs and cache keys for file-based storage.

Canonical URLs are expected to feed future dedupe and stable ID generation. Fingerprints are expected to support `seen_items`, cache invalidation, and novelty detection. Safe slugs/cache keys protect file storage from path traversal and unsafe filenames.

This layer does not fetch source data, rank items, detect trends, call LLMs, generate reports, send email, or write to a database.

## Connector Layer And Fetch Pipeline

Step 6 introduces connector contracts under `src/airi/connectors/` and a sequential fetch pipeline under `src/airi/pipeline/`.

Connector contract:

- `fetch_raw()` returns raw source payloads as `RawSourceItem` objects.
- `normalize()` converts one `RawSourceItem` into one `IntelligenceItem`.
- `fetch_and_normalize()` wraps the two phases, records `ConnectorResult`, and isolates item-level normalization errors.

The fetch pipeline runs connectors sequentially for now, aggregates normalized items, records source health, and optionally writes small JSON/JSONL state files through `StateStore`:

- `latest_items.jsonl`
- `source_health.json`
- `last_run.json`

Failure behavior is source-isolated by default: one connector error does not stop the whole run. Strict mode exists for CI/debugging and raises when any connector reports errors.

`FakeConnector` is the only connector in this step. It is deterministic and intended for smoke tests, CLI checks, and pipeline tests. Real arXiv, GitHub, Hacker News, OpenReview, RSS/company blog, and Devpost connectors will be added after the base contract is stable.

## First Real Source Connector: arXiv

Step 7 adds `ArxivConnector` as the first real external source connector. It uses the public arXiv Atom API for metadata-only fetching and does not download PDFs.

The connector is config-driven through `configs/sources.yml`:

- `queries`
- `categories`
- `max_results`
- `freshness_days`
- `enabled`

Fetched Atom entries become `RawSourceItem` objects, then normalize into `IntelligenceItem` contracts with source metadata, paper signals, payload hashes, content fingerprints, canonical arXiv abs URLs, authors, categories, and published timestamps.

The connector remains low-cost by keeping small limits, sorting by submitted date, using a polite User-Agent, and sleeping briefly between multiple query requests. It is intentionally defensive: malformed entries are skipped and connector-level errors are isolated by the base fetch pipeline.

## Repository Metadata Source: GitHub

Step 8 adds `GitHubConnector` as the first repository metadata source. It uses GitHub Search Repositories API and deliberately avoids cloning repositories, fetching file trees, downloading archives, or reading repository contents.

The connector is config-driven through `configs/sources.yml`:

- `queries`
- `min_stars`
- `max_results`
- `freshness_days`
- `enabled`

Repository records become `RawSourceItem` objects, then normalize into `IntelligenceItem` contracts with canonical repo URLs, GitHub signals, source metadata, payload hashes, content fingerprints, topics/language keywords, owner organization, and repository full name.

The design remains low-cost and GitHub Actions friendly: small search limits, optional `GH_TOKEN`/`GITHUB_TOKEN`, metadata-only records, and source-isolated pipeline errors.

## Ecosystem Signal Sources: Hacker News And Company RSS

Step 9 adds two metadata-only ecosystem signal sources.

`HackerNewsConnector` captures community attention around AI agents, coding agents, LLM infrastructure, protocols, and developer tools. It reads official Hacker News Firebase API story metadata only. It does not crawl comments or scrape linked pages.

`CompanyBlogsConnector` captures official company and lab movement from configured RSS/Atom feeds. It reads feed entry metadata only and does not scrape full article pages.

Both connectors are config-driven, low-cost, and source-isolated by the fetch pipeline. Their outputs feed the same `RawSourceItem` and `IntelligenceItem` contracts as arXiv and GitHub, preserving payload hashes, source metadata, canonical URLs, source-specific signals, and content fingerprints.

## Research Review And Opportunity Sources

PR 10 completes the current ingestion layer with two optional metadata sources.

`OpenReviewConnector` adds public research-review metadata from configurable venues and query terms. It is defensive because OpenReview content schemas differ across venues, and it never downloads PDFs.

`DevpostConnector` adds hackathon/opportunity metadata from configured listing URLs. It is intentionally best-effort and disabled by default because Devpost page structure may change. It does not aggressively crawl or scrape unrelated pages.

Both connectors plug into the same `BaseConnector` and `FetchPipeline` contracts, preserving source health, raw payload hashes, source metadata, canonical URLs, and normalized `IntelligenceItem` outputs.

## Intelligence Layer

PR 11 introduces the first deterministic intelligence processing layer after ingestion.

Components:

- `DedupeEngine` removes duplicate `IntelligenceItem` objects using exact IDs, canonical URLs, source-specific keys, content fingerprints, and conservative near-title matching.
- `NoveltyTracker` reads and updates `seen_items.json` through `StateStore`, separating read-only novelty computation from explicit state updates.
- `TopicExtractor` uses configured topic keywords from `configs/topics.yml` and records `ExtractionMetadata` with method `RULE`.
- `EntityExtractor` uses built-in known entities plus optional watchlists and records `ExtractionMetadata` with method `RULE`.

This layer is deterministic and intentionally does not use LLMs, embeddings, vector databases, ranking models, trend detection, paper-repo linking, or cross-source correlation. Those capabilities remain deferred.

Dedupe preserves evidence by returning duplicate groups with representative IDs, removed duplicate IDs, reasons, and confidence scores. Topic/entity extraction preserves existing item fields and appends extracted values rather than deleting prior metadata.
