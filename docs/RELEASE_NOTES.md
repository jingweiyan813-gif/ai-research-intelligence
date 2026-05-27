# Release Notes

## v0.1.0

v0.1.0 completes the first usable personal AI Research Intelligence loop.

### Completed Capabilities

- Multi-source metadata connectors: arXiv, GitHub, Hacker News, company RSS/blogs, OpenReview, and Devpost.
- Sequential fetch pipeline with source health and JSON/JSONL state.
- Deterministic normalization, fingerprinting, and safe cache keys.
- Dedupe, novelty tracking, rule-based topic extraction, and rule-based entity extraction.
- Explainable scoring/ranking with ranking profiles.
- Trend engine, cross-source correlation, and heuristic paper-repo linking.
- Deterministic Markdown reports: weekly, ecosystem, and alerts.
- SMTP email preview/send support with environment-variable secrets.
- GitHub Actions schedules for weekly radar, ecosystem radar, urgent alerts, and eval.
- Lightweight eval metrics and sample gold labels.

### Known Limitations

- No LLM summarization yet.
- No dashboard or web app.
- No database, vector database, or graph database.
- Eval gold set is sample-only and should be customized for real measurement.
- Devpost and OpenReview are best-effort optional sources and may be less stable.
- Scoring is a deterministic baseline, not a learned ranking model.
- Connectors are metadata-first and intentionally avoid PDF downloads, repo cloning, and full-page scraping.

### Next Roadmap

- Optional LLM-assisted summaries with strict evidence grounding.
- Better eval datasets and regression checks for ranking quality.
- More robust source-specific parsing and connector backoff.
- Optional report templates for different research interests.
- Better trend history visual summaries in Markdown.
