Where data lives decides how fast you can train, how much you pay and which tools you can use. Exam
questions in this area usually hide the answer in the **data type** (structured vs unstructured), the
**access pattern** (analytics scans vs single-row lookups vs files streamed into training) and the
**scale**.

## The storage services, from an ML point of view

| Service | What it is | ML role |
|---|---|---|
| **Cloud Storage** | Object storage (buckets) | Unstructured data (images, audio, video, documents), training files (TFRecord, CSV, Parquet, JSONL), model artifacts, pipeline roots, exported models |
| **BigQuery** | Serverless analytics warehouse | Structured/tabular training data, feature engineering in SQL, BigQuery ML, offline feature store, prediction outputs |
| **Bigtable** | Wide-column NoSQL, single-digit ms at huge scale | Low-latency key lookups at serving time (user profiles, real-time features), time series; Feature Store online serving backend |
| **Spanner** | Globally consistent relational DB | Transactional source systems; vector search on operational data |
| **Cloud SQL / AlloyDB** | Managed PostgreSQL/MySQL | Operational app data; usually replicated to BigQuery for ML |
| **Filestore / NetApp Volumes** | Managed NFS | Shared file system for training jobs that need POSIX file access at high throughput |
| **Pub/Sub** | Messaging (not storage) | Ingests streaming events into Dataflow → BigQuery / Bigtable |

## Getting data into training

- **Custom training** reads from **Cloud Storage**, **BigQuery** or **NFS**. Cloud Storage buckets are
  available to training code as a mounted file system under `/gcs/<bucket>` (Cloud Storage FUSE), so
  frameworks can read files directly.
- Reading BigQuery from TensorFlow/Python: BigQuery Storage Read API (fast, parallel, Arrow/Avro) — e.g.
  the TensorFlow I/O BigQuery reader or the BigQuery client with `to_dataframe` for smaller data. For big
  data, avoid exporting huge CSVs; read in parallel or export to TFRecord/Parquet shards.
- **Managed datasets** (Vertex AI datasets) are **required for AutoML** and optional for custom training.
  Image datasets are imported from Cloud Storage with an import file (JSONL/CSV of URIs + labels); tabular
  from BigQuery or CSV in Cloud Storage.

## File formats for training

| Format | When |
|---|---|
| **TFRecord** (sharded) | Large TensorFlow training; efficient sequential reads with `tf.data`; store images as serialized bytes to avoid millions of small files |
| **Parquet / Avro** | Columnar/row-oriented exchange with Spark, BigQuery, pandas |
| **CSV / JSONL** | Small data, interoperability; JSONL is common for batch prediction and LLM tuning data |
| Individual image files | Fine for AutoML / small sets; for large-scale training, millions of small files are slow — pack them into TFRecords |

Shard files (e.g. 100–200 MB each, many files) so many workers can read in parallel.

## Splitting data

- **Random split** — i.i.d. data only.
- **Chronological split** — anything with time (forecasting, fraud, churn): train on the past, validate
  on the future. Random splits leak future information.
- **Group/entity split** — keep all rows of the same user/patient/device in one split to avoid leakage.
- **Stratified split** — keep class ratios for rare classes.
- AutoML tabular supports random, manual (your split column) and chronological splits.

## ⚖️ BigQuery vs Cloud Storage vs Bigtable

| Question asks for… | Choose |
|---|---|
| SQL analytics, aggregations, joins over TBs; tabular training data | BigQuery |
| Images, audio, video, documents, model artifacts, TFRecords | Cloud Storage |
| Millisecond lookups of features for online prediction at high QPS | Bigtable (or Feature Store online serving on Bigtable) |
| Transactional, globally consistent app data | Spanner |
| Shared POSIX file system for training | Filestore / NetApp Volumes |

## ⚖️ Cloud Storage classes (cost questions)

| Class | Use |
|---|---|
| Standard | Hot data, active training sets |
| Nearline (≥30 days) | Accessed ~monthly |
| Coldline (≥90 days) | Accessed ~quarterly |
| Archive (≥365 days) | Compliance archives, raw data kept "just in case" |

Lifecycle rules move old raw data to colder classes automatically.

## 🪤 Exam traps

- **Bigtable for analytics** or **BigQuery for millisecond serving lookups** — both wrong way round.
- **Millions of small image files** read one by one during training → slow input pipeline; use sharded
  TFRecords.
- **Random split on temporal data** → over-optimistic evaluation (leakage).
- **Copying BigQuery data to CSV** just to train when you can read BigQuery directly or use BigQuery ML.
- **Region mismatch** — keep data, training and endpoints in the same region (batch prediction even
  requires input/output and model to be co-located).

## ✅ Key takeaways

- Structured → BigQuery; unstructured & files → Cloud Storage; low-latency lookups → Bigtable.
- Large training sets → sharded TFRecord/Parquet, parallel reads.
- AutoML needs a managed dataset; custom training can read GCS, BigQuery, NFS.
- Split by time or entity whenever rows aren't independent.
