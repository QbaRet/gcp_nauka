BigQuery ML (BQML) lets you create, train, evaluate, explain and use models with **SQL**, inside BigQuery.
Its exam value is simple: when data already lives in BigQuery and the people building the model know SQL,
BQML avoids exporting data, avoids managing infrastructure and lets analysts do ML. Expect questions on
*which model type* fits a business problem, *how* to engineer features in SQL, and *how predictions reach
applications*.

## How it works

```sql
-- 1. Train (the label is named via input_label_cols or a column called "label")
CREATE OR REPLACE MODEL `proj.ds.churn_model`
TRANSFORM(
  ML.QUANTILE_BUCKETIZE(age, 5) OVER () AS age_bucket,
  ML.FEATURE_CROSS(STRUCT(country, plan)) AS country_plan,
  * EXCEPT (age, country, plan)
)
OPTIONS (model_type = 'BOOSTED_TREE_CLASSIFIER',
         input_label_cols = ['churned'],
         auto_class_weights = TRUE,
         data_split_method = 'AUTO_SPLIT') AS
SELECT * FROM `proj.ds.customers`;

-- 2. Evaluate, 3. Predict, 4. Explain
SELECT * FROM ML.EVALUATE(MODEL `proj.ds.churn_model`);
SELECT * FROM ML.PREDICT(MODEL `proj.ds.churn_model`, TABLE `proj.ds.new_customers`);
SELECT * FROM ML.EXPLAIN_PREDICT(MODEL `proj.ds.churn_model`, TABLE `proj.ds.new_customers`);
```

Training and prediction are billed as BigQuery compute. BigQuery ML is not available in the BigQuery
Standard edition.

## Model types (what to pick for which problem)

| Problem | BQML model type |
|---|---|
| Predict a number | `LINEAR_REG`, `BOOSTED_TREE_REGRESSOR`, `RANDOM_FOREST_REGRESSOR`, `DNN_REGRESSOR`, `AUTOML_REGRESSOR` |
| Predict a class / probability | `LOGISTIC_REG`, `BOOSTED_TREE_CLASSIFIER`, `RANDOM_FOREST_CLASSIFIER`, `DNN_CLASSIFIER`, `DNN_LINEAR_COMBINED_*` (wide & deep), `AUTOML_CLASSIFIER` |
| Customer segmentation (no labels) | `KMEANS` |
| Recommendations from user–item interactions | `MATRIX_FACTORIZATION` (+ `ML.RECOMMEND`) |
| Time-series forecasting | `ARIMA_PLUS` (single or many series, holidays, seasonality), `ARIMA_PLUS_XREG` (with external regressors), **TimesFM** via `AI.FORECAST` (no training) |
| Anomaly detection | `KMEANS`, `PCA`, `AUTOENCODER`, `ARIMA_PLUS` with `ML.DETECT_ANOMALIES` |
| Dimensionality reduction / embeddings | `PCA`, `AUTOENCODER`, `MATRIX_FACTORIZATION` |
| "Why did this metric change?" | Contribution analysis |
| Use a model trained elsewhere | **Imported**: TensorFlow, TensorFlow Lite, ONNX, XGBoost (from Cloud Storage) |
| Call a model hosted elsewhere (incl. Gemini) | **Remote model** pointing at a Vertex AI endpoint / Google model |

Boosted trees, random forest, DNN, wide & deep, autoencoder and AutoML models are *externally trained* —
BigQuery ML orchestrates training on Vertex AI for you, still via SQL.

## Key functions

| Function | Use |
|---|---|
| `ML.EVALUATE` | Metrics (precision, recall, ROC AUC, log loss, R², MAE…) on the evaluation split or a table you pass |
| `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE` | Classifier diagnostics, threshold choice |
| `ML.PREDICT` | Batch predictions as a query result |
| `ML.FORECAST` / `AI.FORECAST` | Forecast future values (ARIMA_PLUS / TimesFM) |
| `ML.EXPLAIN_PREDICT` | Prediction + per-row feature attributions |
| `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE` | Model-level importance (feature importance for tree models) |
| `ML.DETECT_ANOMALIES` | Flag anomalies with k-means / PCA / autoencoder / ARIMA_PLUS |
| `ML.RECOMMEND` | Recommendations from matrix factorization |
| `ML.TRAINING_INFO`, `ML.TRIAL_INFO` | Training iterations; hyperparameter-tuning trials |
| `ML.VALIDATE_DATA_SKEW`, `ML.VALIDATE_DATA_DRIFT` | Compare serving data with training data / earlier data |
| `ML.TRANSFORM` | Apply a model's TRANSFORM preprocessing to new data |
| Generative functions (`ML.GENERATE_TEXT`, `AI.GENERATE…`, `AI.GENERATE_EMBEDDING`) | Call Gemini / embedding models on table rows through remote models |

## Feature engineering with TRANSFORM

The `TRANSFORM` clause inside `CREATE MODEL` defines preprocessing (bucketizing, scaling, feature crosses,
one-hot, imputation…) **once**. BigQuery stores it with the model and **automatically applies the same
transformations in `ML.EVALUATE` and `ML.PREDICT`**. That is BigQuery ML's answer to training-serving
skew: you never re-implement preprocessing at prediction time. Useful helpers: `ML.QUANTILE_BUCKETIZE`,
`ML.BUCKETIZE`, `ML.STANDARD_SCALER`, `ML.MIN_MAX_SCALER`, `ML.FEATURE_CROSS`, `ML.POLYNOMIAL_EXPAND`,
`ML.NGRAMS`, `ML.IMPUTER`. BigQuery ML also one-hot encodes string columns and standardises numeric ones
automatically for many model types.

## Hyperparameter tuning, class imbalance, splits

- Set `NUM_TRIALS` (and optionally `MAX_PARALLEL_TRIALS`) plus search spaces such as
  `learn_rate = HPARAM_RANGE(0.01, 0.1)` to tune; inspect trials with `ML.TRIAL_INFO`. Supported for
  linear/logistic, DNN, wide & deep, boosted trees, random forest, k-means, matrix factorization and
  autoencoder — not PCA.
- `AUTO_CLASS_WEIGHTS = TRUE` re-weights classes for imbalanced data.
- `DATA_SPLIT_METHOD`: `AUTO_SPLIT`, `RANDOM`, `CUSTOM` (your own split column), `SEQ` (time-ordered — use
  for temporal data to avoid leakage), `NO_SPLIT`.

## Getting predictions to applications

| Need | How |
|---|---|
| Nightly / periodic scoring | Scheduled query with `ML.PREDICT` writing to a table |
| Low-latency online predictions | **Register the model in Vertex AI Model Registry** (`model_registry = 'vertex_ai'` option, no export needed) and deploy it to an endpoint |
| Serve outside Google Cloud / on your own infra | `EXPORT MODEL ... OPTIONS(URI='gs://...')` — TensorFlow SavedModel for most types, XGBoost Booster for boosted trees / random forest |

Not exportable: ARIMA_PLUS, TimesFM, remote models, imported ONNX/TF Lite models; export is also blocked
if training used ARRAY, TIMESTAMP or GEOGRAPHY features. TRANSFORM models export with a `transform/`
SavedModel for the preprocessing.

## Remote models: Gemini and Google AI APIs from SQL

BigQuery ML can call models it doesn't host through a **remote model**:

```sql
CREATE OR REPLACE MODEL `proj.ds.gemini`
  REMOTE WITH CONNECTION `proj.eu.vertex_conn`
  OPTIONS (endpoint = 'gemini-2.5-flash');

SELECT * FROM ML.GENERATE_TEXT(MODEL `proj.ds.gemini`,
  (SELECT CONCAT('Classify the sentiment of: ', review) AS prompt FROM `proj.ds.reviews`),
  STRUCT(0.0 AS temperature, TRUE AS flatten_json_output));
```

- Requires a **Cloud resource connection**; its service account needs the Vertex AI User role.
- Generative functions: `ML.GENERATE_TEXT`, the newer `AI.GENERATE` / `AI.GENERATE_TABLE` (structured
  output), and `ML.GENERATE_EMBEDDING` / `AI.GENERATE_EMBEDDING` for embeddings.
- Remote models over **Cloud AI APIs**: `ML.UNDERSTAND_TEXT` (Natural Language), `ML.TRANSLATE`,
  `ML.ANNOTATE_IMAGE` (Vision, via object tables over Cloud Storage), `ML.PROCESS_DOCUMENT` (Document AI),
  `ML.TRANSCRIBE` (Speech-to-Text).
- **Semantic search in the warehouse**: store embeddings in a column, build a **vector index**
  (`CREATE VECTOR INDEX`) and query with `VECTOR_SEARCH` — RAG without leaving BigQuery.

This is the exam's answer to "run gen AI / AI APIs over millions of rows that are already in BigQuery,
without building a pipeline".

## Operating BQML models

- **Retraining**: a scheduled query running `CREATE OR REPLACE MODEL`, or a Vertex AI pipeline using the
  BigQuery ML components (create model → evaluate → compare → register/deploy).
- **Threshold**: `ML.PREDICT(MODEL m, TABLE t, STRUCT(0.7 AS threshold))` changes the decision threshold of
  a binary classifier (default 0.5) without retraining; choose it from `ML.ROC_CURVE`.
- **Monitoring**: `ML.VALIDATE_DATA_SKEW` (vs training statistics) and `ML.VALIDATE_DATA_DRIFT` (vs an
  earlier serving window); `ML.TFDV_DESCRIBE` for statistics.
- **Evaluate clustering** with the Davies-Bouldin index from `ML.EVALUATE` (lower is better) to choose `k`.
- **Cost**: training and prediction scan data like any query — select only needed columns and use
  partitioned/clustered tables.

## ⚖️ BigQuery ML vs AutoML vs custom training

| | BigQuery ML | Vertex AI AutoML | Custom training |
|---|---|---|---|
| Who builds it | Analysts with SQL | Anyone with labelled data | ML engineers |
| Data location | Must be in BigQuery | Cloud Storage / BigQuery (managed dataset) | Anywhere |
| Data movement | None | Imported into a managed dataset | Read by your code |
| Model choice | You pick a type | Searched for you | Unlimited |
| Best for | Tabular, time series, quick baselines, in-warehouse scoring | Strong tabular/image models with no ML code | Special architectures, unstructured data at scale |

## 🧪 Worked scenarios

### 1. Segments without labels
Marketing wants to group 20 M customers by behaviour; there is no label column and data is in BigQuery.
How do you build and pick the number of segments?

**Answer:** `KMEANS` in BigQuery ML; train with a few values of `num_clusters` and compare the
**Davies-Bouldin index** from `ML.EVALUATE` (or tune `num_clusters` with `NUM_TRIALS`). Assign customers
with `ML.PREDICT`.

### 2. 5 000 store-product series
Forecast daily demand for every store × product pair, accounting for holidays.

**Answer:** One `ARIMA_PLUS` model with `TIME_SERIES_ID_COL = ['store','product']` and
`HOLIDAY_REGION`; read forecasts with `ML.FORECAST`. If there are useful external signals (price,
promotions) use `ARIMA_PLUS_XREG`; for zero-training forecasts `AI.FORECAST` (TimesFM).

### 3. Mobile app needs < 100 ms predictions
A BQML boosted-tree model must answer requests from a mobile backend in real time.

**Answer:** Register it in **Vertex AI Model Registry** (`model_registry = 'vertex_ai'`) and **deploy to
an endpoint**. `ML.PREDICT` is a query, not a low-latency serving path.

### 4. Sentiment of 3 M reviews in BigQuery
Analysts want sentiment per review without exporting data or writing Python.

**Answer:** A **remote model** — `ML.UNDERSTAND_TEXT` over the Natural Language API, or Gemini via
`ML.GENERATE_TEXT` / `AI.GENERATE` with a prompt — run directly on the table.

### 5. Precision too low
A churn classifier flags too many loyal customers. The business wants fewer false alarms.

**Answer:** Raise the decision threshold in `ML.PREDICT` (`STRUCT(0.7 AS threshold)`) chosen from
`ML.ROC_CURVE` — no retraining needed.

## 🪤 Exam traps

- **Exporting to CSV to train elsewhere** when BigQuery ML would do — almost always the wrong answer for
  a SQL-skilled team with data in BigQuery.
- **Re-implementing preprocessing in the app** for BQML predictions instead of using `TRANSFORM`.
- **Random split on time series** → leakage. Use `SEQ` / a custom time-based split, or ARIMA_PLUS.
- **Online prediction from BQML** isn't `ML.PREDICT` in a request path — register the model to Vertex AI
  Model Registry and deploy to an endpoint.
- **Recommendations** in BQML = matrix factorization (implicit feedback such as clicks/time spent, or
  explicit ratings).
- **Forecasting many series** (per store, per product): a single ARIMA_PLUS model with
  `TIME_SERIES_ID_COL` trains them all.
- **Remote model fails with a permission error** — the *connection's* service account needs access to
  Vertex AI (and to Cloud Storage for object tables), not just your user.
- **Retraining by hand** — schedule `CREATE OR REPLACE MODEL` or orchestrate with Vertex AI Pipelines.

## ✅ Key takeaways

- BigQuery ML = ML with SQL, no data movement, analysts can own it.
- TRANSFORM keeps training and serving preprocessing identical.
- ARIMA_PLUS / TimesFM for forecasting, matrix factorization for recommendations, k-means for
  segmentation, boosted trees as a strong tabular default.
- Online serving goes through Vertex AI Model Registry + endpoint; export only when you must serve
  elsewhere.
