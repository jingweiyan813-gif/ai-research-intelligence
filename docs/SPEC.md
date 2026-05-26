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
