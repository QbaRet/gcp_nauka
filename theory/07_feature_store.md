Good features beat clever models, and on the exam "feature engineering" questions are mostly about three
things: **encoding** data correctly, **avoiding leakage and skew**, and **sharing/serving features**
consistently — which is what Vertex AI Feature Store is for.

## Feature engineering essentials

| Data | Technique | Notes |
|---|---|---|
| Numeric with different scales | Standardisation (z-score) or min-max scaling | Needed for linear models / neural nets / distance-based models; not for trees |
| Skewed numeric (income, counts) | Log transform, bucketing (quantile buckets) | Reduces the influence of outliers |
| Low-cardinality categorical | One-hot encoding | |
| High-cardinality categorical (user IDs, zip codes) | **Embeddings**, hashing (feature hashing / hash buckets) | One-hot explodes dimensionality |
| Interactions (city × time of day) | **Feature crosses** | Lets linear models learn non-linear combinations |
| Text | Tokenisation, n-grams, TF-IDF, embeddings | Or let a foundation model handle raw text |
| Timestamps | Day of week, hour, holidays, cyclical (sin/cos) encoding | |
| Missing values | Impute (mean/median/mode) + "is_missing" indicator | Compute impute values on training data only |
| Geographic | Bucketised lat/long + crosses | |

**Feature selection**: remove features that leak the label, are unavailable at prediction time, are
near-constant or are highly correlated duplicates; use feature importance / attributions to prune.

## Leakage: the silent killer

A feature leaks if it contains information that **won't be available at prediction time** or that is a
proxy for the label (e.g. "account_closed_date" when predicting churn). Symptoms: suspiciously high
validation accuracy that collapses in production. Fixes: build features only from data available at
prediction time, use **point-in-time** joins, and split by time.

## Vertex AI Feature Store (current, BigQuery-based)

The current Feature Store (often called *V2*) uses **BigQuery as the offline store** — no separate offline
storage is provisioned. Concepts:

| Resource | Meaning |
|---|---|
| **Feature group** | Points at one BigQuery table/view; has entity ID column(s) and, for time-series data, a timestamp column |
| **Feature** | A column in a feature group (registration is optional, but needed to serve the latest value when IDs repeat, to pick specific columns, to aggregate sources or to monitor feature drift) |
| **Online store** (`FeatureOnlineStore`) | The serving cluster (node count etc.) |
| **Feature view** | Collection of features in an online store, **periodically synced** from BigQuery (scheduled or continuous sync) |
| **Feature monitor** | Scheduled stats & drift detection for features |

Online serving types:

| | **Bigtable online serving** | Optimized online serving (**deprecated**) |
|---|---|---|
| Best for | Large data volumes (TBs), high durability | Ultra-low latency, embeddings |
| Sync | Scheduled and continuous | Scheduled only |
| Embeddings / vector search | No — use **Vector Search** | Yes (being retired) |
| Status | Recommended | Deprecated, sunset Feb 17, 2027 |

Training data: query BigQuery with **point-in-time correctness** — for each training example, use the
feature values as they were *at that example's timestamp*, never later. This prevents leakage and
mirrors what the online store would have served.

**Feature Store (Legacy)** — the older version with featurestores, entity types and separate ingestion —
is deprecated (Feb 17, 2026; shutdown Feb 17, 2027). Older exam questions describe it; the concepts
(entities, online/offline serving, point-in-time lookups, sharing features across teams) carry over.

## Why use a feature store (what the exam wants to hear)

- **Reuse & discovery**: teams share curated features instead of rebuilding them.
- **Consistency**: same feature definitions for training (offline) and serving (online) → less
  training-serving skew.
- **Low-latency online serving** of fresh feature values to endpoints.
- **Point-in-time** training datasets without leakage.
- **Feature monitoring** for drift.

## ⚖️ Where to compute features

| Need | Where |
|---|---|
| Aggregates over historical data (30-day spend) | BigQuery SQL / scheduled queries → feature group |
| Real-time aggregates from events (clicks in last 5 min) | Dataflow streaming from Pub/Sub → BigQuery / Bigtable |
| Transformations that must be identical at serving | Inside the model (Keras layers), tf.Transform, or BQML TRANSFORM |
| Features shared by many models / teams, served online | Feature Store |

## ⚖️ Encoding categorical features

| Cardinality | Encoding |
|---|---|
| A handful of values | One-hot |
| Hundreds–thousands | Embeddings or hashing |
| Ordered categories (S/M/L) | Ordinal encoding |
| Unknown values at serving | Out-of-vocabulary bucket |

## 🪤 Exam traps

- **Normalising with statistics from all data** (train + test) → leakage. Fit scalers on training data.
- **Features not available at serving time** (e.g. computed after the event) → great offline metrics,
  useless model.
- **One-hot encoding user IDs** → huge sparse vectors; use embeddings/hashing.
- **Scaling for tree models** is unnecessary — don't pick it as the "fix".
- **Embeddings in Feature Store**: for new work, Google recommends Vector Search rather than the deprecated
  Optimized online serving.

## ✅ Key takeaways

- Encode by data type and cardinality; crosses and embeddings are standard tools.
- Leakage = information unavailable at prediction time; use point-in-time joins and time-based splits.
- Feature Store (V2): BigQuery offline store, feature groups/views, online store on Bigtable, sync from
  BigQuery; legacy version deprecated.
- Feature stores exist for reuse, consistency (less skew) and online serving.
