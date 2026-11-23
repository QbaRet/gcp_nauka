Domain 5 (~18–22 % of the exam) is about turning notebooks into **repeatable, automated pipelines** and
retraining models without humans in the loop. Know Vertex AI Pipelines well, the MLOps maturity levels,
how pipelines get triggered, and how CI/CD/CT fit together.

## Vertex AI Pipelines

Serverless orchestration of ML workflows. A pipeline is a **DAG of containerised steps** (components)
linked by inputs/outputs; independent tasks run in parallel by default.

- **SDKs**: **Kubeflow Pipelines (KFP) v2** or **TensorFlow Extended (TFX)**. Google's guidance: use
  **TFX** if you use TensorFlow on **terabytes of structured or text data**; otherwise use the **KFP SDK**.
- **Google Cloud Pipeline Components** — ready-made components for Vertex AI services (AutoML training,
  custom jobs, batch prediction, endpoint deployment, BigQuery, Dataflow…).
- **Lifecycle**: define components and pipeline in Python → **compile** to a YAML pipeline spec →
  submit a `PipelineJob` (with `pipeline_root` in Cloud Storage and parameter values) → monitor → done.
  Compiled templates can be stored and shared in a repository (e.g. Artifact Registry) and reused.
- **Lineage**: every parameter and artifact is recorded in **Vertex ML Metadata** automatically.

### Execution caching
A step is skipped when ML Metadata already has an execution with the same **cache key** — built from
the step's **inputs** (parameter values, input artifact IDs), **output definitions** and the **component
spec** (image, command, args, env). Only pipelines with the **same name** share the cache, and there's no
TTL. Disable per task (`task.set_caching_options(False)`) or per run (`enable_caching=False`).
Non-deterministic steps (e.g. "read latest data") must not rely on the cache or they will be skipped
unexpectedly.

### Scheduling and triggering

| Trigger | How |
|---|---|
| Time-based | **Scheduler API** (`PipelineJob.create_schedule()`) with a cron expression; pause/resume (optional catch-up), max concurrent runs, start/end time |
| Event-based (new data, drift alert, message) | **Pub/Sub** → **Cloud Run functions** (Cloud Functions) that calls `PipelineJob(...).submit()` with the compiled template |
| New files in Cloud Storage | Storage event → function → pipeline |
| Code change | **Cloud Build** trigger on the repository → build, test, compile, deploy/run pipeline |
| Monitoring alert | Model Monitoring alert → Pub/Sub → function → retraining pipeline |

### Other orchestrators

| Tool | Use |
|---|---|
| **Vertex AI Pipelines** | Container-native ML workflows with KFP/TFX running in Google Cloud |
| **Cloud Composer / Managed Service for Apache Airflow** | End-to-end workflows that unify **data engineering and ML** (many non-ML tasks, existing Airflow DAGs); can trigger Vertex AI pipelines |
| **Kubeflow Pipelines on GKE** | Self-managed; only when you need to run on your own cluster |
| **Ray on Vertex AI** | Distributed Python (data processing, training, tuning) with the Ray framework |

## MLOps maturity levels (Google's model)

| Level | What it looks like |
|---|---|
| **0 — Manual** | Notebooks and scripts, manual hand-off from data scientists to engineers, infrequent releases, **no CI/CD**, only the prediction service is deployed, little monitoring |
| **1 — ML pipeline automation** | **Continuous training (CT)**: the training pipeline is automated and triggered; automated **data and model validation**; modular, containerised components; **metadata** management; you deploy the **pipeline**, not just the model |
| **2 — CI/CD pipeline automation** | Automated **CI** (build & test components and pipeline), **CD** (deploy pipeline to environments), automated triggering, model CD, monitoring; source control, model registry, feature store, metadata store, orchestrator |

**CT** (continuous training) is the property unique to ML systems. CI in ML also tests **data, schemas
and models**, not only code.

## Retraining policy

Retrain:
- **on a schedule** (stable, predictable drift),
- **when enough new data** has arrived,
- **on performance degradation** (when ground truth labels arrive and metrics drop),
- **on detected drift/skew** (Model Monitoring alert) — a proxy when labels are delayed.

Every retrain should pass **validation gates**: data validation (schema, distributions — e.g. TFDV),
model evaluation against the **current production model** (champion/challenger), and only then
deployment (often canary). Promotion: register the new version, move the alias, shift traffic.

## CI/CD/CT with Cloud Build

Typical flow: commit → **Cloud Build** runs unit tests for components, builds container images
(push to **Artifact Registry**), compiles the pipeline, runs it in a test project → on approval, deploys
the pipeline/schedule to production. Environments: automated to test, semi-automated to pre-prod,
manual approval to production.

## Writing a pipeline with KFP v2

```python
from kfp import dsl, compiler

@dsl.component(base_image="python:3.11", packages_to_install=["pandas", "scikit-learn"])
def train(data: dsl.Input[dsl.Dataset], model: dsl.Output[dsl.Model],
          metrics: dsl.Output[dsl.Metrics]) -> float:
    ...                      # read data.path, write model.path
    metrics.log_metric("auc", auc)
    return auc

@dsl.pipeline(name="churn-training")
def pipeline(min_auc: float = 0.8):
    data = extract().set_caching_options(False)      # non-deterministic → no cache
    t = train(data=data.outputs["dataset"]).set_cpu_limit("8").set_memory_limit("32G")
    with dsl.If(t.outputs["Output"] >= min_auc):      # gate
        deploy(model=t.outputs["model"])

compiler.Compiler().compile(pipeline, "pipeline.yaml")
```

- **Lightweight Python components** (decorated functions) for simple steps; **container components** for
  any image/language; **Google Cloud Pipeline Components** for Vertex AI services.
- Typed artifacts — `Dataset`, `Model`, `Metrics`, `ClassificationMetrics` — are tracked in ML Metadata.
- Control flow: `dsl.If` / `dsl.Elif` / `dsl.Else`, `dsl.ParallelFor` (fan-out, e.g. one model per
  region), `dsl.ExitHandler` (always run cleanup/notification).
- Resources per step (`set_cpu_limit`, `set_memory_limit`, accelerators) — heavy training usually runs as
  a **CustomJob component** instead of inside the step container.

## A typical continuous-training pipeline

1. **Extract** new data (BigQuery) — caching off.
2. **Validate** data: schema and distribution checks; stop if anomalies.
3. **Transform** / build features (Dataflow, BigQuery or tf.Transform).
4. **Train** (custom job / AutoML / BQML), optionally with **hyperparameter tuning**.
5. **Evaluate** on a holdout and **compare with the champion** model.
6. If better: **register** the version in Model Registry (alias `challenger` → `champion`).
7. **Deploy** with a canary traffic split; configure **monitoring**.
8. **Notify** (ExitHandler) on success or failure.

## ⚖️ Kubeflow Pipelines vs TFX

| | KFP SDK | TFX |
|---|---|---|
| Frameworks | Any (PyTorch, XGBoost, sklearn, TF, custom) | TensorFlow-centric |
| Building blocks | Your own components + Google Cloud Pipeline Components | Standard components: ExampleGen, StatisticsGen, SchemaGen, ExampleValidator, **Transform**, Trainer, Tuner, **Evaluator** (TFMA), InfraValidator, Pusher |
| Pick when | General-purpose ML workflows | TensorFlow on TB-scale structured/text data, need built-in validation and tf.Transform |

## ⚖️ Vertex AI Pipelines vs Composer (Airflow)

| | Vertex AI Pipelines | Composer / Managed Airflow |
|---|---|---|
| Focus | ML steps, artifacts, lineage | General workflow orchestration (ETL + ML) |
| Lineage & ML metadata | Built in | Not ML-aware |
| Infrastructure | Serverless | Managed Airflow environment |
| Pick when | Training/eval/deploy workflows | Data engineering team already runs Airflow, many non-ML tasks |

## 🧪 Worked scenarios

### 1. Weekly retraining reuses old data
A weekly scheduled pipeline finishes in seconds and the model never changes; the extract step's inputs
are identical each week.

**Answer:** **Execution caching** reuses the earlier extract result. Disable caching on the
non-deterministic step (or pass the run date as a parameter).

### 2. Deploy only if better
Retrained models must never replace the production model unless they beat it on the latest holdout.

**Answer:** An **evaluation component** comparing challenger vs champion, followed by a **`dsl.If`**
gate before register/deploy (then canary).

### 3. New files trigger training
Partners drop new CSV files into a bucket at unpredictable times; training should start automatically.

**Answer:** Cloud Storage event → **Cloud Run function** (or Eventarc) → submit the compiled
`PipelineJob`.

### 4. The data team already runs Airflow
Hundreds of ETL DAGs run in Composer; ML training must start after the ETL finishes.

**Answer:** Keep orchestration in **Composer** for ETL and have it **trigger a Vertex AI pipeline** for
the ML part (lineage, ML artifacts).

### 5. "Minimal ops" Kubeflow
A team wants Kubeflow Pipelines without managing Kubernetes.

**Answer:** **Vertex AI Pipelines** (serverless KFP) instead of Kubeflow on GKE.

## 🪤 Exam traps

- **Cron on a VM / manual notebook runs** for retraining — use Scheduler API or event triggers.
- **Caching skipping "get latest data"** steps — disable caching for non-deterministic steps.
- **Deploying a retrained model without comparing it to production** — add an evaluation gate.
- **Self-managed Kubeflow on GKE** when the requirement is "minimal operational overhead" → Vertex AI
  Pipelines.
- **Retraining on every drift alert without validation** can deploy worse models.
- **Doing heavy training inside a lightweight component's container** instead of a CustomJob / GPU
  resources.
- **No notification on failure** — use an ExitHandler / Cloud Monitoring alerts on pipeline failures.

## ✅ Key takeaways

- Vertex AI Pipelines = serverless KFP/TFX DAGs with automatic lineage; compile → PipelineJob.
- Caching keys on inputs + spec; disable for non-deterministic steps.
- Triggers: Scheduler API (time), Pub/Sub + function (events), Cloud Build (code).
- MLOps level 1 = continuous training; level 2 = CI/CD of the pipeline itself.
- Always gate deployment with data validation and champion/challenger evaluation.
