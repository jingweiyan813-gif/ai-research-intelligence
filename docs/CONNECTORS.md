# CONNECTORS

Step 6 defines the connector framework only. It does not implement real external connectors and does not call external APIs.

## Connector Contract

Every connector should subclass `BaseConnector` and provide:

- `name`: stable connector name, for example `arxiv` or `github` in future steps.
- `source`: `SourceType` enum value.
- `connector_version`: connector implementation version, defaulting to `v1`.
- `fetch_raw(since=None, limit=None)`: returns `list[RawSourceItem]`.
- `normalize(raw)`: converts one `RawSourceItem` into one `IntelligenceItem`.

`fetch_and_normalize()` is implemented by the base class and should usually not be reimplemented. It records:

- source
- raw count
- normalized count
- errors
- started timestamp
- completed timestamp

## Error Isolation

Connector-level `fetch_raw()` errors are captured in `ConnectorResult.errors` and return zero items. Item-level normalization errors are also captured, but other raw items continue to normalize.

The fetch pipeline continues after connector errors by default. Strict mode raises a `RuntimeError` when any connector reports errors.

## Source Health

When `FetchPipeline.run(save=True)` is used, state is written through `StateStore`:

- `data/state/latest_items.jsonl`
- `data/state/source_health.json`
- `data/state/last_run.json`

`source_health.json` includes raw count, normalized count, error count, errors, and timestamps for each source.

## FakeConnector

`FakeConnector` is deterministic and exists only for tests and smoke checks:

```bash
airi fetch fake
airi fetch fake --limit 5 --no-save
```

It must not be treated as a real source connector. Concrete connectors for arXiv, GitHub, Hacker News, OpenReview, RSS/company blogs, and Devpost will be added later.

## arXiv Connector

`ArxivConnector` is the first real connector and is implemented in `src/airi/connectors/arxiv.py`.

Scope:

- Uses `https://export.arxiv.org/api/query`.
- Fetches metadata only.
- Does not download PDFs.
- Does not call LLMs.
- Does not score, dedupe, or rank papers.

Config fields are read from the arXiv source entry in `configs/sources.yml`:

- `queries`: keyword searches converted to `all:"..."` arXiv queries.
- `categories`: category searches converted to `cat:<category>` queries.
- `max_results`: default request/result cap.
- `freshness_days`: default recency filter.
- `enabled`: disables the connector when false.

Normalization behavior:

- arXiv PDF and abs URLs canonicalize to `https://arxiv.org/abs/<id>`.
- `RawSourceItem.raw_payload` keeps id, title, summary, authors, categories, published, updated, links, and primary category.
- `IntelligenceItem` uses `ItemType.PAPER`, `SourceType.ARXIV`, `SourceMetadata`, `SignalBundle`, `PaperSignals`, `source_payload_hash`, and `content_fingerprint`.

CLI smoke command:

```bash
airi fetch arxiv --limit 2 --no-save
```

Concrete connectors for GitHub, Hacker News, OpenReview, RSS/company blogs, and Devpost remain out of scope for this step.
