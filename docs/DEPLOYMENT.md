# Deployment / 部署指南

这个项目推荐作为低成本个人 AI Research Radar 运行在 GitHub Actions 上。

## 1. 配置 GitHub Secrets

在 GitHub 仓库中打开 **Settings → Secrets and variables → Actions → New repository secret**，添加：

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `REPORT_FROM_EMAIL`
- `REPORT_TO_EMAIL`

可选：

- `GH_TOKEN` 或 `GITHUB_TOKEN`，用于提高 GitHub API rate limit。

不要提交 `.env`、`*.local.yml`、SMTP password、API key 或私人笔记路径。

## 2. 启用 Workflows

工作流位于 `.github/workflows/`：

- `weekly_research.yml`：每周完整技术情报周报。
- `ecosystem_radar.yml`：每两天生态雷达。
- `urgent_alerts.yml`：每日 / 多次提醒检查。
- `eval_weekly.yml`：每周轻量 eval。

这些 workflow 都支持 `workflow_dispatch`，可以在 GitHub Actions 页面手动触发。

## 3. 本地 Dry Run

```bash
python scripts/run_weekly.py --dry-run --no-email
python scripts/run_ecosystem.py --dry-run --no-email
python scripts/run_alerts.py --dry-run --no-email
python scripts/run_eval.py
```

Email preview 不需要 SMTP credentials：

```bash
airi email preview data/reports/weekly/<YYYY-MM-DD>.md
airi email send data/reports/weekly/<YYYY-MM-DD>.md --dry-run
```

## 4. 推荐手动 Pipeline

真实本地运行或手动 Actions 运行时，推荐使用 `fetch all`，避免单来源 fetch 覆盖 `latest_items.jsonl`：

```bash
airi fetch all --limit-per-source 10
airi intelligence dedupe
airi intelligence extract
airi intelligence novelty --update-seen
airi rank --profile intelligence --top 10
airi trends --update-timeseries
airi correlate --apply
airi report weekly
```

GitHub Actions 会运行完整 pipeline scripts，并在有变化时提交 `data/reports` 和 `data/state`。

## 5. 成本说明

系统使用公开 metadata API、本地 JSON/JSONL state、Markdown reports 和 Email。不需要服务器、数据库、向量数据库、dashboard 或 LLM API。仍需注意 GitHub Actions 免费额度和公开来源 API rate limit。

## 6. 安全说明

- Workflows 使用最小化的 `contents: write` 权限提交报告和状态。
- Bot identity 固定为 `ai-research-radar-bot <bot@example.com>`。
- Secrets 通过环境变量注入，不在日志中 echo。
- Email reports 可能暴露你的研究兴趣，请谨慎选择收件人。
