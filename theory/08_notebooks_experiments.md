Domain 2 of the exam is about *collaboration*: prototyping in secure notebooks, tracking experiments so
results are reproducible and comparable, and keeping lineage of what data and code produced which model.
The services: **Vertex AI Workbench**, **Colab Enterprise**, **Vertex AI Experiments**, **Vertex AI
TensorBoard**, **Vertex ML Metadata** and **Model Registry**.

## Notebook environments

### Vertex AI Workbench (instances)
JupyterLab on a Compute Engine VM you configure (machine type, GPUs, disk, network), with TensorFlow and
PyTorch preinstalled, conda environments or custom containers.
- Built-in **BigQuery** and **Cloud Storage** browsing; query BigQuery from JupyterLab.
- **Scheduled executions** (executor): run a notebook once or on a schedule on Vertex AI training
  hardware; results go to Cloud Storage — even while the instance is off.
- **Idle shutdown** on by default (cost control).
- GitHub sync, Dataproc (Spark) integration, VPC, **CMEK**, Confidential Computing, Workforce Identity.
- **Managed notebooks** and **user-managed notebooks** are the older Workbench types — deprecated in
  January 2024, support ended April 2025, and they were removed/converted in March 2026. Today the answer
  is **Workbench instances**.

### Colab Enterprise
Managed, collaborative notebooks (Colab UX) with Google Cloud security: runtimes are **provisioned on
demand** and shut down when idle; **runtime templates** define machine type, accelerators and disk.
Notebooks are stored regionally and shared with **IAM**; you can create one straight from the BigQuery
editor; Gemini helps write code; notebooks can run on a schedule. Code runs with the user's credentials
by default.

### Notebooks on Dataproc
JupyterLab with **Spark kernels** on a Dataproc cluster (or Serverless Spark) — for PySpark exploration of
big data.

### Security & collaboration best practices
- One instance per user (or Colab Enterprise with IAM sharing); don't share a single VM login.
- Use service accounts with least privilege; restrict who can act as them.
- Private IPs / VPC, **VPC Service Controls** to prevent data exfiltration, CMEK for encryption.
- Keep code in **Git** (Workbench GitHub integration) — notebooks are not a version-control system.
- Turn on idle shutdown; schedule long jobs as executions or training jobs rather than leaving VMs on.

## Reproducibility checklist

To reproduce a model months later you need to pin **all** of:

| What | How |
|---|---|
| Code | Git commit hash, logged as a parameter of the experiment run |
| Environment | Container image **digest** in Artifact Registry; pinned package versions |
| Data | Table snapshot / partition date / time travel, or versioned files in Cloud Storage; managed dataset version |
| Randomness | Fixed seeds (and note that GPU ops can still be non-deterministic) |
| Hyperparameters & metrics | Vertex AI Experiments run |
| Provenance | Vertex AI Pipelines → ML Metadata lineage automatically |

## From notebook to production

1. Explore and prototype in Workbench / Colab Enterprise.
2. Move logic into **Python modules with tests**; keep the notebook as a thin driver.
3. Package as a **container** (or prebuilt container + source distribution).
4. Run as a **training job**, then compose jobs into a **Vertex AI pipeline**.
5. Trigger the pipeline on schedule/events; deploy through CI/CD.

Scheduled notebook executions are fine for reports and lightweight recurring jobs, but production
training belongs in pipelines (testable, versioned, with lineage).

## Comparing and evaluating models

- **Model evaluation** in Vertex AI attaches evaluation metrics to model versions in the Registry, so you
  can compare versions (and AutoML vs custom) in one place.
- Pipelines can log metrics artifacts (`Metrics`, `ClassificationMetrics`) that the console renders
  (confusion matrix, ROC curve) and that show up in Experiments.

## ⚖️ Workbench vs Colab Enterprise vs Dataproc notebooks

| | Workbench instance | Colab Enterprise | Dataproc notebooks |
|---|---|---|---|
| Model | Long-lived VM you manage | Managed runtimes on demand | Cluster with Spark |
| Best for | Custom environments, GPUs, long-running interactive work, full control | Quick, collaborative, zero-setup notebooks, sharing via IAM | Big-data exploration with Spark |
| Customisation | High (VM, containers, conda) | Runtime templates | Cluster config, Spark |
| Scheduling | Executor | Scheduled runs | Via jobs/workflows |

## Experiment tracking: Vertex AI Experiments + TensorBoard

- An **experiment** groups **experiment runs** (and pipeline runs). A run records **parameters**,
  **summary metrics** (one value per key, e.g. final AUC), **time-series metrics** (per step, stored in
  **Vertex AI TensorBoard**), and artifacts/executions.
- Compare runs side by side in the console or with the SDK
  (`aiplatform.init(experiment=...)`, `start_run`, `log_params`, `log_metrics`, `log_time_series_metrics`).
- TensorFlow has deep integration; other frameworks use the framework-neutral SDK. Pipeline runs can be
  associated with an experiment.
- **Vertex AI TensorBoard** is a managed TensorBoard: training curves, profiling, shared across the team.

## Lineage: Vertex ML Metadata

Metadata is a graph: **artifacts** (datasets, models, metrics) and **executions** (steps that ran) are
nodes, **events** connect artifacts as inputs/outputs of executions, and **contexts** group them (e.g. a
pipeline run or experiment). Vertex AI Pipelines record all parameters and artifacts in ML Metadata
automatically, so you can answer: *which data, code and hyperparameters produced this model, and what
was it used for later?* It is built on the open-source ML Metadata (MLMD) library from TFX.

## Model Registry: versions and aliases

Central place for models (custom, AutoML, BigQuery ML — BQML models can be registered without export):
- **Versions** of the same model; **aliases** such as `default` (the version used when none is specified)
  or your own (`champion`, `challenger`, `staging`).
- From a version: view evaluation metrics, deploy to an endpoint, or run batch prediction.
- Use aliases to promote a version to production without changing client code.

## ⚖️ Which tool answers which question

| Question | Tool |
|---|---|
| "Compare hyperparameters & metrics of many training runs" | Vertex AI Experiments |
| "Visualise loss curves / profile training" | Vertex AI TensorBoard |
| "Which dataset version produced this model?" / audit trail | Vertex ML Metadata (lineage) |
| "Keep versions of a model, promote one to production" | Model Registry (versions + aliases) |
| "Share a notebook securely with a colleague" | Colab Enterprise (IAM) / Git for code |

## 🧪 Worked scenarios

### 1. GPU notebook left on
Data scientists leave A100 Workbench instances running over weekends.

**Answer:** Enable **idle shutdown**, move long runs to **scheduled executions / training jobs**, or use
**Colab Enterprise** runtimes that are provisioned on demand.

### 2. Audit question
An auditor asks which dataset and code version produced the model currently in production.

**Answer:** **Vertex ML Metadata lineage** (recorded automatically by Vertex AI Pipelines) plus the
Model Registry version; log the Git commit in the run.

### 3. 300 tuning runs
A team runs hundreds of experiments with different hyperparameters and needs to compare AUC and loss
curves.

**Answer:** **Vertex AI Experiments** (params + summary metrics) with **Vertex AI TensorBoard** for
time-series metrics.

### 4. Notebook with sensitive data
Notebooks query patient data in BigQuery; security requires that data can't be copied out of the
project.

**Answer:** **VPC Service Controls** perimeter around BigQuery, Cloud Storage and Vertex AI; Workbench
with private IP, a least-privilege service account and CMEK if required.

## 🪤 Exam traps

- **Choosing managed or user-managed notebooks** — retired; Workbench instances or Colab Enterprise.
- **Tracking experiments in spreadsheets / file names** — use Vertex AI Experiments.
- **Lineage ≠ experiment tracking**: lineage (ML Metadata) is about provenance between artifacts;
  Experiments is about comparing runs.
- **Leaving GPU notebooks running** — idle shutdown, schedule executions, or submit training jobs.
- **Exfiltration risk from notebooks** — VPC Service Controls + private networking.
- **Production jobs running under a personal user account** — use a dedicated service account.
- **"Reproducible" without data versioning** — logging code and params isn't enough if the table changed.

## ✅ Key takeaways

- Workbench instances = configurable JupyterLab VMs; Colab Enterprise = managed, collaborative runtimes.
- Experiments (params/metrics/runs) + TensorBoard (curves) for comparing runs.
- ML Metadata = lineage graph of artifacts, executions, contexts.
- Model Registry = versions + aliases + deploy/evaluate/batch predict.
