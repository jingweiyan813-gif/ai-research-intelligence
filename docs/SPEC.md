# SPEC

AIRI 的系统路线是：

`Source -> Normalize -> Dedupe -> Enrich -> Score -> Trend -> Report -> Email`

当前 Step 3 定义的是数据契约层，不实现真实连接器、抓取、归一化算法、评分算法、LLM、报告生成、邮件发送、数据库或仪表盘。

## Model Overview

模型位于 `src/airi/models/`：

- `enums.py`：统一枚举，包括来源类型、条目类型、趋势类型、建议动作和抽取方法。
- `source.py`：`SourceMetadata`，记录来源、原始 URL、connector 名称与版本、抓取时间和 payload hash。
- `raw.py`：`RawSourceItem`，表示尚未归一化的原始来源条目。
- `evidence.py`：`EvidenceRef`，用于让趋势声明和报告内容引用具体证据条目。
- `extraction.py`：`ExtractionMetadata`，记录 topics、entities、keywords 等抽取过程的方法、版本和置信度。
- `signals.py`：`SignalBundle` 和 source-specific signals，承载论文、GitHub、社区、黑客松、公司公告等模块化信号。
- `scores.py`：`ScoreBundle` 和 `ScoreBreakdown`，保留总分、维度分和可读解释。
- `item.py`：`IntelligenceItem`，归一化后的核心情报条目。
- `trend.py`：`TopicTrend` 和 `TrendClaim`，用于描述主题趋势和有证据支持的趋势判断。
- `report.py`：`Report` 和 `ReportSection`，定义未来报告的结构。

## Traceability

每个 `IntelligenceItem` 都必须包含 `source_metadata`，并且 `source_metadata.source` 必须与 item 自身的 `source` 一致。`source_payload_hash` 和 `content_fingerprint` 分别用于追踪原始 payload 和归一化内容指纹。

## Evidence-Grounded Reporting

`TrendClaim` 必须包含至少一个 `EvidenceRef`。未来报告章节可以通过 `evidence_item_ids` 引用情报条目，避免生成没有证据支撑的结论。

## Explainable Ranking

`ScoreBundle` 不只保存 `final_score`，还保存 topic relevance、quality、freshness、popularity、novelty、momentum、personal relevance 和 cross-source correlation 等维度。`ScoreBreakdown` 为每个维度记录 reason 和 evidence item IDs，保证未来排序结果可解释。

## Extraction Metadata

抽取结果需要可审计。`ExtractionMetadata` 记录 `method`、`extractor_name`、`extractor_version`、`extracted_at` 和可选 `confidence`，用于区分规则、LLM、人工或混合抽取。

## Modular Source Signals

`SignalBundle` 将通用信号和来源特定信号分离：

- `CommonSignals`：新鲜度和来源重要性。
- `PaperSignals`：论文分类、会议/期刊、代码可用性和引用数。
- `GitHubSignals`：stars、forks、近期提交、issues 和最后 push 时间。
- `CommunitySignals`：Hacker News 分数与评论数。
- `HackathonSignals`：截止时间、奖金和远程参与信息。
- `CompanySignals`：公司名称和是否官方公告。

这种结构让后续新增来源时可以扩展 signals，而不需要破坏核心 `IntelligenceItem` 契约。

## Normalization Responsibilities

The normalization layer provides deterministic utilities shared by future pipeline stages:

- Text normalization keeps punctuation meaningful for technical terms while removing noisy punctuation for matching.
- URL normalization removes tracking parameters, fragments, unnecessary trailing slashes, and source-specific URL variants.
- arXiv canonicalization maps PDF and abs links to `https://arxiv.org/abs/<id>` while preserving version suffixes such as `v2`.
- GitHub canonicalization maps issue, pull, blob, and tree URLs back to `https://github.com/<owner>/<repo>` for repo-level dedupe.
- Payload hashing uses stable JSON serialization with sorted keys.
- Content fingerprints normalize title/body text before hashing so whitespace-only changes do not create new identities.
- Safe slugs and cache keys avoid path separators, path traversal markers, and unsafe filename characters.

Connectors should produce raw data, then call normalization utilities before building `IntelligenceItem` contracts. Dedupe, stable IDs, `seen_items`, cache keys, and future novelty detection should use canonical URLs and fingerprints from this layer.

## Dedupe, Novelty, And Rule Extraction

PR 11 adds deterministic intelligence utilities that operate on `IntelligenceItem` models after fetch.

### Dedupe

Dedupe responsibilities:

- Remove exact ID duplicates.
- Remove canonical URL duplicates.
- Apply source-specific dedupe for arXiv, GitHub, Hacker News, OpenReview, and Devpost.
- Remove matching content fingerprints.
- Apply conservative near-title matching only for same source or same canonical domain.
- Select a representative item by preferring scores, richer source signals, newer fetch time, then original order.
- Return duplicate groups with explainable reasons and confidence.

### Novelty

Novelty responsibilities:

- Read `seen_items.json` without mutating it during `compute()`.
- Compare incoming items by item ID, canonical URL, and content fingerprint.
- Return deterministic novelty scores: new items are high novelty, exact seen items are low novelty, and fingerprint repeats are low novelty.
- Update `seen_items.json` only when explicitly requested.

### Rule-Based Topic Extraction

Topic extraction responsibilities:

- Read configured primary and negative topics.
- Match title, abstract, snippet, keywords, and entities with normalized deterministic text.
- Preserve existing topics and append extracted topics.
- Record `ExtractionMetadata` with `method=RULE`, extractor name, version, timestamp, and confidence.

### Rule-Based Entity Extraction

Entity extraction responsibilities:

- Use built-in company/lab, benchmark, protocol, and tool names.
- Optionally extend known entities from watchlists.
- Preserve existing entities and append extracted entities.
- Record `ExtractionMetadata` with `method=RULE`, extractor name, version, timestamp, and confidence.

No LLM, embeddings, vector database, scoring, trend engine, report generation, or external API calls are part of this layer.

## Trend Engine And Cross-Source Responsibilities

PR 13 adds basic research-intelligence responsibilities after scoring/ranking.

### Trend Engine

The trend engine reads normalized/scored items and computes topic-level metrics over a recent window:

- current item count and source count
- paper, repo, Hacker News/community, and company counts
- previous-window count from `topic_timeseries.json`
- growth rate, bounded momentum score, novelty score, and trend type
- representative item IDs ordered by score and recency

Non-noise trends produce deterministic `TrendClaim` objects. Each claim must include evidence references, confidence, and numeric metrics. This makes future reports evidence-grounded instead of free-form assertions.

### Cross-Source Correlation

Cross-source correlation groups items by topic and measures whether that topic appears across multiple source categories. A topic seen in papers plus repos plus community/company updates receives a stronger signal than a topic seen in only one source. Applying correlation updates existing `ScoreBundle.cross_source_correlation`; final score recomputation only happens when scoring weights are available.

### Paper-Repo Linking

Paper-repo linking uses local metadata only. It can link by exact repo mention, arXiv ID mention, strong distinctive token overlap, or shared distinctive entities. It intentionally ignores generic terms such as `agent`, `llm`, `rag`, `ai`, `benchmark`, and `framework` to reduce over-linking.

This PR does not call LLMs, generate final reports, send email, schedule GitHub Actions, add a database, fetch GitHub README files, or download papers.

## Markdown Report Generation Responsibilities

PR 14-A turns existing local intelligence outputs into deterministic markdown artifacts.

### Inputs

Reports read only local state and in-memory analysis outputs:

- `latest_items.jsonl`
- ranked/scored `IntelligenceItem` objects
- `TrendClaim` objects with evidence refs
- `CrossSourceSignal` objects
- `PaperRepoLink` objects

### Report Types

- Weekly reports provide the broadest view: summary, ranked items, source/category sections, trends, correlations, links, and recommended actions.
- Ecosystem reports focus on repos, community discussions, company/lab updates, hackathons, and cross-source ecosystem signals.
- Alerts reports select high-signal items above the configured alert threshold, strong cross-source signals, and soon-ending hackathons.

### Constraints

Report generation must be deterministic and evidence-aware. Trend claims included in reports must show evidence item IDs or titles. No LLM calls, email sending, GitHub Actions schedules, external APIs, databases, vector databases, graph databases, dashboards, or eval frameworks are part of PR 14-A.
