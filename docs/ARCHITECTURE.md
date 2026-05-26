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
