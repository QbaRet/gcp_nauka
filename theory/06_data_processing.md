The exam guide asks you to *choose the right preprocessing tool based on scale and complexity* —
BigQuery SQL, Dataflow, Apache Spark or in-memory Python — and to *ensure consistent preprocessing
between training and serving*. Most questions are tool-selection questions with one decisive detail:
streaming vs batch, existing Spark code, SQL skills, or "no-code".

## The tools

### BigQuery (SQL)
Serverless, scales to petabytes, no cluster. Ideal for joins, aggregations, window functions, filtering
and feature engineering on structured data. Scheduled queries for recurring jobs. If data is already in
BigQuery and the transformation is expressible in SQL, this is usually the simplest answer.

### Dataflow (Apache Beam)
Fully managed, **unified batch and streaming** processing. You write a Beam pipeline (Java, Python, Go);
Dataflow autoscales workers and rebalances work, deletes workers when the job finishes, and processes
**exactly-once** by default (at-least-once optional for streaming to cut cost/latency). Run your own code,
**templates** (Google-provided or yours) or iterate in notebooks.
ML uses: heavy preprocessing of unstructured data (images, text) at scale, **streaming feature
computation** from Pub/Sub, **TensorFlow Transform** (tf.Transform runs on Beam/Dataflow), and
**RunInference** for batch/stream inference inside a Beam pipeline.

### Dataproc (managed Spark/Hadoop)
Managed clusters for Spark, Hadoop, Hive, Pig and friends (current docs title: *Managed Service for Apache
Spark*). Clusters start/scale/stop in ~90 s, per-second billing, preemptible/Spot workers for cost.
**Serverless Spark** runs Spark batches without managing clusters.
Pick it when the team **already has Spark/Hadoop jobs** (lift-and-shift without rewriting), uses
Spark MLlib, or needs Spark kernels in notebooks.

### Cloud Data Fusion
Visual, code-free data integration (built on open-source CDAP): pipelines are DAGs of sources,
transforms and sinks, batch or real-time. Runs on ephemeral Spark clusters it provisions per run.
Pick it for **no-code/low-code ETL** by data-integration teams with many connectors.

### Dataprep
Visual data wrangling/cleaning (by Trifacta/Alteryx, a partner product; Google's docs now redirect to the
vendor's documentation). Appears in older questions as the "analysts clean data visually" answer.

### In-memory Python (pandas, scikit-learn)
Perfectly fine for data that fits on one machine (Workbench/Colab). The exam penalises it only when data
is large or the process must be production-grade and repeatable.

### Pub/Sub
Global messaging for event ingestion; decouples producers from Dataflow consumers. Pub/Sub + Dataflow +
BigQuery/Bigtable is the canonical streaming architecture.

## Consistent preprocessing between training and serving

Training-serving skew often comes from implementing the same transformation twice (Python in training,
Java in the app). Ways to do it once:

| Approach | How it guarantees consistency |
|---|---|
| **BigQuery ML TRANSFORM** | Stored with the model, applied automatically in ML.PREDICT |
| **TensorFlow Transform (TFX Transform)** | Computes full-pass statistics (mean, vocab) with Beam, exports a transform graph that is attached to the serving model |
| **Keras preprocessing layers** inside the model | Preprocessing becomes part of the SavedModel |
| **Feature Store** | Features computed once, served to both training (point-in-time) and online inference |
| **Same container/library** for batch & online paths | Shared code, e.g. a custom prediction routine with preprocessing |

## Streaming concepts (Dataflow / Beam)

| Concept | Meaning |
|---|---|
| **Event time vs processing time** | When the event happened vs when the pipeline sees it. Aggregate on **event time** for correct features |
| **Fixed (tumbling) windows** | Non-overlapping, e.g. every 5 minutes |
| **Sliding (hopping) windows** | Overlapping, e.g. "last 10 minutes, updated every minute" — typical for real-time features |
| **Session windows** | Per-key activity separated by a gap of inactivity (user sessions) |
| **Watermark** | Pipeline's estimate that all data up to time T has arrived |
| **Triggers / allowed lateness** | When to emit results, and how late data still updates them |

Typical real-time feature: Pub/Sub → Dataflow (sliding window per card/user) → Bigtable or Feature Store
online store, and the same values written to BigQuery for training.

## TensorFlow Transform in detail

tf.Transform has two phases:

1. **Analyze** — a full pass over the training data on Beam/Dataflow computes statistics: mean/std,
   min/max, quantiles, **vocabularies**.
2. **Transform** — applies those constants row by row. The result is a **transform graph** saved with the
   model, so serving uses exactly the same constants.

Common functions: `tft.scale_to_z_score`, `tft.scale_to_0_1`, `tft.compute_and_apply_vocabulary`,
`tft.bucketize`, `tft.tfidf`. Use it when preprocessing needs **full-pass statistics** — something Keras
layers inside a single training step can't compute without an `adapt()` pass.

## Orchestrating SQL transformations

For SQL-heavy pipelines in BigQuery: **scheduled queries** for simple recurring jobs, **Dataform** (SQL
workflows with dependencies, tests/assertions and Git) for larger transformation graphs, and Composer or
Vertex AI Pipelines when SQL steps are part of a bigger ML workflow.

## ⚖️ BigQuery vs Dataflow vs Dataproc vs Data Fusion

| Scenario | Best fit |
|---|---|
| Structured data in BigQuery, SQL-able transformations | **BigQuery** |
| Streaming events, windowing, late data, real-time features | **Dataflow** (+ Pub/Sub) |
| Batch + streaming with one codebase, autoscaling, no cluster ops | **Dataflow** |
| Existing Spark/Hadoop jobs, MLlib, migrate from on-prem Hadoop | **Dataproc** (or Serverless Spark) |
| Visual no-code ETL with many connectors | **Data Fusion** |
| Data fits in memory, exploration | pandas in Workbench / Colab Enterprise |
| Full-pass statistics (vocabularies, z-scores) applied identically at serving | **TensorFlow Transform** on Dataflow |

## ⚖️ Dataflow cost & performance levers

| Lever | Effect |
|---|---|
| Autoscaling (horizontal) and right-sized worker machine types | Pay for what the pipeline needs |
| Flexible Resource Scheduling (FlexRS) for batch | Cheaper batch jobs with delayed start |
| At-least-once streaming mode | Lower cost/latency if duplicates are acceptable |
| Avoid hot keys / fusion bottlenecks; use Combine instead of GroupByKey where possible | Better parallelism |
| Templates | Reusable, parameterised, launchable from pipelines/Cloud Functions |

## 🧪 Worked scenarios

### 1. Real-time fraud feature
The fraud model needs "number of transactions per card in the last 10 minutes" at prediction time.

**Answer:** **Pub/Sub → Dataflow** with a **sliding window** keyed by card on event time, writing to a
low-latency store (Bigtable / Feature Store online) — and to BigQuery for training.

### 2. 200 PySpark jobs
A company migrates from on-prem Hadoop and wants to move 200 PySpark jobs with minimal changes.

**Answer:** **Dataproc** (or Serverless for Apache Spark). Rewriting in Beam for Dataflow contradicts
"minimal changes".

### 3. Vocabulary at serving time
A TensorFlow text model needs the training vocabulary and z-score constants applied identically online.

**Answer:** **TensorFlow Transform** — analyze phase on Dataflow, transform graph exported with the
model.

### 4. Nightly joins in BigQuery
5 TB of order data in BigQuery must be joined and aggregated into a feature table every night.

**Answer:** **BigQuery SQL** as a scheduled query (or Dataform for a larger dependency graph). No need
for Dataflow or Spark.

### 5. Analysts without code
A data-integration team wants to build pipelines from SaaS sources and databases visually.

**Answer:** **Cloud Data Fusion**.

## 🪤 Exam traps

- **Rewriting Spark jobs in Beam** when the requirement is "migrate quickly with minimal code changes" →
  Dataproc.
- **Dataproc for brand-new streaming pipelines** with no Spark constraint → Dataflow is managed and unified.
- **Computing normalisation statistics on the full dataset before splitting** → leakage; compute on the
  training split (tf.Transform does this inside the training pipeline).
- **Duplicated preprocessing in the serving app** → training-serving skew. Prefer TRANSFORM / tf.Transform /
  in-model layers / Feature Store.
- **Cloud Functions for heavy data processing** — fine for small triggers/glue, not for large-scale ETL.
- **Processing-time windows for behavioural features** — late events land in the wrong window; use
  event time with watermarks.
- **Computing vocabularies per batch** — full-pass statistics need tf.Transform (or BigQuery) over the
  whole training set.

## ✅ Key takeaways

- SQL-able + in BigQuery → BigQuery. Streaming or unified batch/stream → Dataflow. Existing Spark →
  Dataproc. No-code ETL → Data Fusion.
- Pub/Sub → Dataflow → BigQuery/Bigtable is the standard streaming pattern.
- Implement preprocessing once (TRANSFORM, tf.Transform, Keras layers, Feature Store) to avoid skew.
