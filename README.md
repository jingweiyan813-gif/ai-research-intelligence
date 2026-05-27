# AI Research Intelligence System

![CI](https://github.com/jingweiyan813-gif/ai-research-intelligence/actions/workflows/eval_weekly.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

一句话定位：一个低成本、GitHub Actions 驱动的 AI 技术情报系统，用于追踪 AI Agent、Coding Agent、DevTools 和 LLM Infrastructure 的论文、项目、公司动态、社区热点和黑客松机会。

## 项目定位

这个项目不是：

- 不是 AI News Bot：不追求泛新闻聚合和快讯轰炸。
- 不是 RSS Digest：不只是把 feed 拼成列表。
- 不是 LLM Wrapper：v0.1 不调用 LLM，也不依赖 prompt 生成结论。

它是一个 Multi-source AI Research Intelligence System：从多个公开来源收集 metadata，统一成可追溯的数据契约，进行确定性去重、抽取、排序、趋势分析、跨源关联和报告生成。

## 为什么做这个项目

AI 技术信息源已经过载：GitHub Trending、Hacker News、arXiv、OpenReview、公司博客、黑客松平台都很分散。普通 newsletter 通常不够个性化，也很难解释“为什么这个条目重要”。

本项目目标是构建一个高信噪比、可追溯、可自动运行的技术情报流：

- 自动追踪公开来源。
- 保留每条情报的来源和证据。
- 用确定性规则优先，避免黑盒排序。
- 通过 GitHub Actions 定时运行。
- 通过 Email 作为唯一通知渠道。

## 核心能力

- 多源采集：arXiv、GitHub、Hacker News、Company RSS、OpenReview、Devpost。
- 统一数据契约：`IntelligenceItem`、`SourceMetadata`、`EvidenceRef`、`ScoreBundle`。
- 去重与 novelty：基于 ID、canonical URL、fingerprint 和 seen state。
- Topic / Entity extraction：基于配置和内置 watchlist 的规则抽取。
- Explainable scoring / ranking：每个分数维度都有 `ScoreBreakdown`。
- Trend engine：按 topic 计算窗口增长、momentum 和趋势类型。
- Cross-source correlation：识别同一主题是否跨论文、repo、社区、公司动态出现。
- Paper-repo linking：启发式连接论文和可能相关的 GitHub repo。
- Markdown reports：周报、生态雷达、提醒报告。
- Email delivery：SMTP plain-text 邮件和 dry-run preview。
- GitHub Actions automation：定时运行、提交报告和状态文件。
- Lightweight eval：precision@k、duplicate rate、evidence coverage 等轻量指标。

## 系统架构

```text
Source
  → Normalize
  → Dedupe
  → Extract
  → Score / Rank
  → Trend / Correlate
  → Report
  → Email / GitHub Actions
```

设计重点是低成本、可解释、可追溯、可在公开 GitHub 仓库中安全运行。

## 当前支持的信息源

- arXiv：论文 metadata，不下载 PDF。
- GitHub：repo metadata，不 clone repo，不抓 file tree。
- Hacker News：story metadata，不抓评论全文。
- Company RSS：公司 / 实验室公开 feed，不抓全文网页。
- OpenReview：公开 note/submission metadata，默认关闭。
- Devpost：hackathon/opportunity metadata，默认关闭。

OpenReview / Devpost 属于可选且 best-effort 的来源，默认 disabled。v0.1 不下载 PDF、不 clone repository、不做 full article scraping。

## 快速开始

```bash
pip install -e ".[dev]"
airi config validate
airi fetch all --limit-per-source 10
airi intelligence dedupe
airi intelligence extract
airi intelligence novelty --update-seen
airi rank --profile intelligence --top 10
airi trends --update-timeseries
airi correlate --apply
airi link paper-repos
airi report weekly
airi report ecosystem
airi report alerts
airi eval ranking
```

真实使用推荐 `airi fetch all`，它会把多个 enabled sources 放进同一个 `FetchPipeline`，并只写一次 `latest_items.jsonl`、`source_health.json` 和 `last_run.json`。单来源命令如 `airi fetch arxiv`、`airi fetch github` 仍然保留，但会覆盖 `latest_items.jsonl`，更适合调试 connector。

## 推荐自用方式

- 本地开发：用 `pip install -e ".[dev]"` 安装，手动跑完整 pipeline。
- 自动运行：用 GitHub Actions 定时执行 scripts。
- 通知渠道：Email 是唯一通知渠道，避免引入 Slack / 飞书 / Telegram 复杂度。
- 私人数据边界：私人笔记、Obsidian vault、private configs 不进入公开仓库。

## GitHub Actions 自动化

需要在 GitHub Secrets 中配置：

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `REPORT_FROM_EMAIL`
- `REPORT_TO_EMAIL`

可选：

- `GH_TOKEN` 或 `GITHUB_TOKEN`：用于 GitHub API 更高 rate limit。

工作流位于 `.github/workflows/`：

- `weekly_research.yml`：每周 AI 技术情报周报。
- `ecosystem_radar.yml`：每两天生态雷达。
- `urgent_alerts.yml`：每日 / 多次提醒检查。
- `eval_weekly.yml`：每周轻量 eval。

## 报告示例

示例周报：`docs/examples/weekly_report_example.md`

生成报告命令：

```bash
airi report weekly
airi report ecosystem
airi report alerts
airi email preview data/reports/weekly/<YYYY-MM-DD>.md
airi email send data/reports/weekly/<YYYY-MM-DD>.md --dry-run
```

## 隐私边界

公开仓库可以保存：

- 代码、默认配置、示例配置。
- 公开来源 metadata 生成的 state / reports。
- sample eval labels 和示例报告。

公开仓库不应该保存：

- `.env`、SMTP 密码、API key。
- `*.local.yml`、`configs/*.local.yml`。
- 私人笔记、Obsidian vault、private docs。
- 任何无法公开的 recipient / credential 信息。

Secrets 只通过环境变量或 GitHub Secrets 注入。Email report 可能暴露你的研究兴趣和关注主题，请谨慎选择收件人。

## 设计取舍

- Deterministic rules first：v0.1 优先使用可测试、可解释的规则。
- No LLM in v0.1：不做 LLM 总结，避免成本、漂移和证据幻觉。
- No database：使用 JSON / JSONL，便于 GitHub Actions 和个人维护。
- No dashboard：报告优先用 Markdown + Email。
- GitHub Actions-first：不需要服务器，低成本定时运行。

## Roadmap

v0.1 已完成：

- multi-source connectors
- fetch pipeline
- dedupe / novelty / extraction
- scoring / ranking profiles
- trend / correlation / paper-repo linking
- markdown reports
- email delivery
- GitHub Actions automation
- lightweight eval

v0.2 可能方向：

- 更好的 eval gold set 和 ranking regression。
- 可选 LLM summary，但必须 evidence-grounded。
- 更稳健的 arXiv / OpenReview 解析和 backoff。
- GitHub Pages report index。
- 可选 dashboard（后置，不作为默认路径）。

## License

MIT License，详见 `LICENSE`。
