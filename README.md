# ai-research-intelligence

## 一句话定位

ai-research-intelligence（简称 AIRI）是一个面向 AI 研究与产品动态的本地优先情报流水线骨架，用于后续把公开来源的信息整理成可追踪、可去重、可评分、可报告的研究线索。

## 这个项目是什么

这是一个 Python 包和命令行工具的 Step 1 skeleton。当前阶段只提供最小可安装项目结构、`airi` CLI 入口、基础健康检查命令、配置样例和开发检查命令，为后续实现研究情报流水线打地基。

规划中的架构路线是：

`Source -> Normalize -> Dedupe -> Enrich -> Score -> Trend -> Report -> Email`

含义如下：

- `Source`：从公开来源获取候选信息。
- `Normalize`：把不同来源整理成统一结构。
- `Dedupe`：合并重复或高度相似的条目。
- `Enrich`：补充元数据、上下文和分类信息。
- `Score`：根据规则或模型给线索打分。
- `Trend`：识别主题、技术和产品趋势。
- `Report`：生成面向阅读和决策的报告。
- `Email`：把报告发送给指定收件人。

## 这个项目不是什么

- 不是新闻机器人。
- 不是 RSS 摘要服务。
- 不是私有笔记搜索器。
- 不是 Obsidian vault 读取工具。
- 不是已经可用的生产级数据库、仪表盘或自动化报告系统。
- 当前不会实现 connectors、scoring、reports、LLM、email、database 或 dashboard。

## 隐私边界

公开仓库只面向公开来源和示例配置，不会读取私人笔记、私人目录或 Obsidian vault。任何涉及私人知识库、个人文件、授权账号或本地敏感数据的能力，都不属于当前公开 skeleton 的默认行为。

## 当前状态

当前状态：Step 1 skeleton。

已包含：

- Python 包结构：`src/airi`
- CLI 入口：`airi`
- 基础命令：`airi --help`、`airi version`、`airi doctor`
- 开发依赖：`pytest`、`ruff`、`mypy`
- 配置样例：`configs/`
- 基础文档：`docs/`

## 本地开发命令

建议使用 Python 3.10+ 创建虚拟环境：

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

常用命令：

```bash
airi --help
airi version
airi doctor
make check
```

单独运行检查：

```bash
python -m pytest
python -m ruff check src tests
python -m mypy src
```

## 配置系统

Step 2 增加了配置加载与校验层，用于在不实现真实抓取、评分、报告或邮件发送的前提下，先固定系统边界和配置结构。

默认配置位于 `configs/`：

- `sources.yml`：公开信息源定义，并要求至少一个 source 处于启用状态。
- `topics.yml`：研究主题与负面主题，并要求至少一个 primary topic。
- `scoring.yml`：评分权重、阈值和数量限制；权重总和必须为 1.0。
- `profile.example.yml`：用户画像示例，不应包含私人资料。
- `email.example.yml`：邮件配置示例，不应包含真实密码、token 或 API key。
- `watchlists.example.yml`：关注列表示例。

可选本地覆盖文件：

- `configs/profile.local.yml`
- `configs/email.local.yml`
- `configs/watchlists.local.yml`

这些 `*.local.yml` 文件可能包含真实值，只用于本地环境，已被 `.gitignore` 排除，不应提交到公开仓库。

配置命令：

```bash
airi config validate
airi config show
```

`airi config show` 只输出脱敏摘要，包括启用的信息源、主要主题、评分权重和本地覆盖文件是否存在，不输出密码、token 或 API key。

## 数据契约层

Step 3 增加了 `src/airi/models/` 数据契约层，用来固定系统内部对象的边界：原始来源条目、归一化情报条目、来源元数据、抽取元数据、证据引用、模块化 signals、可解释 scores、趋势声明和报告结构。

核心原则：

- **可追踪**：每个 `IntelligenceItem` 都必须关联 `SourceMetadata`，保留来源、URL、connector、抓取时间和 payload hash。
- **证据驱动**：`TrendClaim` 必须引用 `EvidenceRef`，未来报告章节也可以引用 evidence item IDs。
- **可解释**：`ScoreBundle` 与 `ScoreBreakdown` 保存维度分、最终分、理由和证据引用。
- **可审计**：`ExtractionMetadata` 记录抽取方法、抽取器名称、版本、时间和置信度。
- **可演进**：`SignalBundle` 将论文、GitHub、社区、黑客松和公司公告 signals 分开，方便后续扩展新来源。

当前仍不实现 connectors、抓取、排序算法、LLM、邮件发送、数据库、向量数据库或 dashboard。

## 轻量存储层

Step 4 增加了 `src/airi/storage/` 文件存储层，用 JSON/JSONL 支撑个人使用和 GitHub Actions 场景，不需要数据库或服务器。

目录边界：

- `data/state`：公开状态文件，可用于保存小型可提交状态，例如 seen items、source health、last run。
- `data/reports`：公开报告输出目录。
- `data/sample`：公开样例数据目录。
- `data/cache`：私有缓存目录，已 gitignore。
- `data/raw`：私有原始数据目录，已 gitignore。

存储命令：

```bash
airi storage doctor
airi storage init
airi storage init --private
```

`airi storage doctor` 只确保公开目录存在并打印路径，不写入真实数据。`airi storage init` 默认只创建公开目录；加 `--private` 才会创建 `data/cache` 和 `data/raw`。

## 归一化层

Step 5 增加了 `src/airi/normalize/` 归一化工具层，用于给后续 connectors、dedupe、fingerprinting 和缓存逻辑提供统一的文本、URL、hash 与 slug 处理能力。

设计边界：

- connectors 不应各自实现临时清洗逻辑，而应调用 `airi.normalize`。
- canonical URL 会用于后续去重、稳定 ID 和来源追踪。
- content fingerprint 和 source payload hash 会用于 `seen_items`、缓存命中和未来 novelty detection。
- safe slug/cache key 会避免路径穿越和不安全文件名。

当前只提供确定性的本地工具函数，不抓取外部数据、不调用 API、不评分、不做趋势算法、不调用 LLM。

## Connector 框架与 Fake Fetch

Step 6 增加了 connector 基类和通用 fetch pipeline。当前只提供 `FakeConnector`，用于测试和 smoke check，不会访问任何外部网络或真实 API。

Connector 合约：

- `fetch_raw()`：返回 `RawSourceItem` 列表。
- `normalize()`：把单个 `RawSourceItem` 转成 `IntelligenceItem`。
- `fetch_and_normalize()`：统一执行抓取与归一化，并记录 counts、errors 和 timestamps。

Fetch pipeline 会按顺序运行 connectors。默认情况下，一个 source 失败不会中断整个 pipeline；使用 `strict=True` 时，如果某个 connector 产生错误则会抛出异常。

Smoke 命令：

```bash
airi fetch fake
airi fetch fake --limit 5 --no-save
```

当保存开启时，pipeline 会写入小型状态文件：`latest_items.jsonl`、`source_health.json` 和 `last_run.json`。当前仍不实现 arXiv、GitHub、Hacker News、OpenReview、RSS、company blogs 或 Devpost 等真实连接器。
