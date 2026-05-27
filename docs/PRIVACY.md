# PRIVACY

AIRI 的公开仓库只面向公开来源的研究情报流水线骨架，不读取私人笔记、私人目录或 Obsidian vault。

## Public Config Boundary

公开配置文件位于 `configs/`，默认只包含示例值和公开来源定义：

- `sources.yml`
- `topics.yml`
- `scoring.yml`
- `profile.example.yml`
- `email.example.yml`
- `watchlists.example.yml`

`email.example.yml` 不允许包含真实密码、token 或 API key。测试和 CLI 校验会把示例邮件配置视为公开文件处理。

## Local Config Boundary

以下本地覆盖文件是可选的，只用于开发者自己的机器：

- `configs/profile.local.yml`
- `configs/email.local.yml`
- `configs/watchlists.local.yml`

这些文件可能包含真实邮箱、收件人或本地偏好，因此已通过 `.gitignore` 排除，不应提交到公开仓库。`airi config show` 只展示本地覆盖文件是否存在，不输出其中的秘密字段。

## Out Of Scope

当前 Step 2 不实现外部 API 调用、真实 source fetching、LLM、邮件发送、数据库、向量数据库或 dashboard，因此不会主动访问私人服务或发送任何数据。

## Storage Boundary

Step 4 separates public state from private raw/cache data:

- `data/state` may contain small public state files that are safe to commit when they do not contain private data.
- `data/reports` may contain generated public-facing reports.
- `data/sample` may contain sample or fixture data.
- `data/cache` is private and gitignored.
- `data/raw` is private and gitignored.

Do not store private Obsidian vault content, personal notes, credentials, cookies, raw private exports, or private API responses in public directories. If future local workflows need raw payloads or temporary API responses, they should use `data/raw` or `data/cache`, which are excluded from version control by default.

## License And Private Data

The MIT License applies to the public code and documentation in this repository only. It does not grant rights over private notes, local configs, secrets, Obsidian vaults, unpublished datasets, or any personal files that are not part of the public repository.

The public repository must never read private notes, Obsidian vaults, local secret configs, or credentials by default. Local-only files such as `.env`, `*.local.yml`, `configs/*.local.yml`, `personal/`, `private/`, `vault/`, `data/raw/`, `data/cache/`, and `.cache/` remain protected by `.gitignore`.

## GitHub Secrets And Email Delivery

PR 14-B uses GitHub Secrets or environment variables for SMTP credentials:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `REPORT_FROM_EMAIL`
- `REPORT_TO_EMAIL`

These values must never be committed to the repository. The CLI and scripts do not print SMTP passwords, API keys, or secrets. Email preview mode writes local `.eml` preview files and does not require real SMTP credentials.

Email delivery sends generated markdown report content to configured recipients. Treat emailed reports as potentially sensitive because they may reveal your interests, watched topics, or public-source reading habits. The public repository still must not read private notes, Obsidian vaults, private local configs, or secrets.
