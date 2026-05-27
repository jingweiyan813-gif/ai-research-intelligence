# Release Notes

## v0.1.0

v0.1.0 完成第一个可用的个人 AI Research Intelligence loop。

### 已完成能力

- 多源 metadata connectors：arXiv、GitHub、Hacker News、Company RSS、OpenReview、Devpost。
- Fetch pipeline：source health、JSON/JSONL state、combined `fetch all`。
- Deterministic normalization、fingerprinting、safe cache keys。
- Dedupe、novelty tracking、rule-based topic/entity extraction。
- Explainable scoring/ranking 和 ranking profiles。
- Trend engine、cross-source correlation、paper-repo linking。
- 中文默认 Markdown reports：weekly、ecosystem、alerts。
- SMTP email preview/send，credentials 仅来自环境变量或 GitHub Secrets。
- GitHub Actions schedules：weekly radar、ecosystem radar、urgent alerts、eval。
- Lightweight eval metrics 和 sample gold labels。

### 已知限制

- 暂无 LLM summarization。
- 暂无 dashboard / web app。
- 暂无 database、vector database、graph database。
- Eval gold set 只是 sample，需要按个人偏好扩展。
- Devpost / OpenReview 是 best-effort optional sources，默认关闭。
- Scoring 是 deterministic baseline，不是 learned ranking model。
- Connectors 只抓 metadata，不下载 PDF、不 clone repo、不抓全文网页。

### 下一步 Roadmap

- 更好的 eval gold set 和 ranking regression checks。
- 可选 LLM summary，但必须 evidence-grounded。
- 更稳健的 arXiv / OpenReview parsing 和 backoff。
- GitHub Pages report index。
- 可选 dashboard（后置，不作为默认路线）。
