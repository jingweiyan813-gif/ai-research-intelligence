# SCORING

PR 12 introduced deterministic, explainable scoring for `IntelligenceItem` objects. PR 13.5 redesigns scoring into explicit ranking profiles so the system can rank differently before and after trend/correlation signals exist.

## Inputs

The scorer uses:

- `configs/scoring.yml` for ranking profiles, thresholds, and limits.
- `active_profile` to choose the default profile.
- `configs/profile.example.yml` or local profile config for interests.
- Existing item fields such as topics, keywords, entities, published time, source signals, novelty scores, momentum, and cross-source correlation.

No LLM, embeddings, external API calls, database, or vector database are used.

## Ranking Profiles

`configs/scoring.yml` defines three profiles. Each profile must sum to `1.0`.

### item_baseline

`item_baseline` is for item-level ranking before trend/correlation exists or when a caller wants source-local ranking. It emphasizes topic relevance, quality, freshness, novelty, and modest popularity/personal relevance. Momentum and cross-source correlation are `0.0` in this profile.

### intelligence

`intelligence` is the default public research intelligence ranking. It emphasizes topic relevance, quality, momentum, and cross-source correlation now that PR 13 provides trend and ecosystem signals. This is the default `active_profile`.

### personal

`personal` is for local user preference reranking. It keeps topic relevance and quality important, but raises `personal_relevance` while still considering momentum and cross-source correlation.

## Popularity Bias

Popularity is intentionally low in the `intelligence` and `personal` profiles. GitHub stars, HN score, and similar metrics are useful signals, but they should not dominate research intelligence ranking or drown out novel/early signals.

## Dimensions

- `topic_relevance`: increases with extracted topics and profile-interest topic matches.
- `quality`: source-specific metadata quality signal.
  - Papers: title/abstract, paper categories, OpenReview venue.
  - Repos: GitHub stars, forks, recent push metadata.
  - Discussions: Hacker News score and comments.
  - Company updates: official announcement and known company name.
  - Hackathons: deadline, remote flag, prize metadata.
- `freshness`: exponential decay based on `published_at` or `fetched_at`.
- `popularity`: source-specific popularity, such as GitHub stars/forks or HN score/comments.
- `novelty`: uses an existing novelty score if present, otherwise defaults to new-item score `1.0`.
- `personal_relevance`: deterministic keyword/topic/entity match against profile interests.
- `momentum`: trend signal emphasized after PR 13; remains deterministic and explainable.
- `cross_source_correlation`: ecosystem signal emphasized after PR 13; measures whether topics appear across source categories.

## Final Score

`final_score` is the weighted sum of the selected ranking profile dimensions, clamped to `[0, 1]`.

Each dimension emits a `ScoreBreakdown` with:

- dimension name
- score
- human-readable reason
- evidence item IDs

## CLI

Use the default profile:

```bash
airi rank --top 10
```

Override the profile explicitly:

```bash
airi rank --profile item_baseline --top 5
airi rank --profile intelligence --top 5
airi rank --profile personal --top 5
```

Invalid profile names fail clearly.

## Ranking

`ItemRanker` sorts by:

1. `final_score` descending
2. `quality` descending
3. `freshness` descending
4. newer `published_at` / `fetched_at`
5. title

This makes ranking deterministic and stable.
