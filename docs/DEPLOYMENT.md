# Deployment

This project can run as a low-cost personal AI research radar on GitHub Actions.

## 1. Configure GitHub Secrets

In your GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `REPORT_FROM_EMAIL`
- `REPORT_TO_EMAIL`

Optional:

- `GH_TOKEN` or `GITHUB_TOKEN` for higher GitHub API rate limits.

Never commit `.env`, `*.local.yml`, SMTP passwords, API keys, or private note paths.

## 2. Enable Workflows

The workflows are in `.github/workflows/`:

- `weekly_research.yml`: weekly full radar report.
- `ecosystem_radar.yml`: every-two-days ecosystem radar.
- `urgent_alerts.yml`: twice-daily alert checks.
- `eval_weekly.yml`: weekly lightweight eval report.

Each workflow also supports `workflow_dispatch`, so you can run it manually from the GitHub Actions UI.

## 3. Local Dry Runs

Run locally without sending email:

```bash
python scripts/run_weekly.py --dry-run --no-email
python scripts/run_ecosystem.py --dry-run --no-email
python scripts/run_alerts.py --dry-run --no-email
python scripts/run_eval.py
```

Preview email without SMTP credentials:

```bash
airi email preview data/reports/weekly/<YYYY-MM-DD>.md
airi email send data/reports/weekly/<YYYY-MM-DD>.md --dry-run
```

## 4. Cost Notes

The system uses public metadata APIs, local JSON/JSONL state, Markdown files, and email. It does not require a server, database, vector database, dashboard, or LLM API. GitHub Actions free-tier limits and source API rate limits still apply.

## 5. Safety Notes

- Workflows use `contents: write` to commit generated reports and state.
- Bot identity is fixed as `ai-research-radar-bot <bot@example.com>`.
- Secrets are passed through environment variables and are not echoed.
- Email reports may reveal your research interests, so choose recipients carefully.

## 6. Recommended Manual Pipeline

For real local or manual GitHub Actions runs, prefer `fetch all` so enabled sources are combined into one latest state file:

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

Single-source fetch commands remain useful for debugging, but they overwrite `latest_items.jsonl`. The scheduled GitHub Actions workflows run the full pipeline scripts and commit generated reports/state when changes exist.
