When AutoML and BigQuery ML aren't enough you run **custom training** on Vertex AI: your code, Google's
managed compute. Exam questions focus on packaging (prebuilt vs custom container), which job type to use,
how to cut cost (Spot VMs), what to do when training fails, and **hyperparameter tuning**.

## Packaging your code

| | **Prebuilt container** | **Custom container** |
|---|---|---|
| What you provide | A Python source distribution or a single Python file | A Docker image (Artifact Registry or Docker Hub) |
| Frameworks | TensorFlow, PyTorch, scikit-learn, XGBoost (specific versions) | Anything — or no framework at all |
| Dependencies | Installed at start from your package's requirements | Pre-installed in the image (faster start, reproducible) |
| Use when | Standard frameworks and versions | Non-Python code, private/system dependencies, unusual versions, exact reproducibility |

The container's `ENTRYPOINT`/`CMD` can be overridden. Training code should read data from Cloud Storage
(mounted under `/gcs/`), BigQuery or NFS, and write the model to the output directory Vertex AI provides
(environment variable `AIP_MODEL_DIR`) so it can be uploaded to the Model Registry.

## Job types

| Resource | What it does |
|---|---|
| **CustomJob** | Runs your training application once; you get artifacts in Cloud Storage |
| **HyperparameterTuningJob** | Runs many trials of your application with different hyperparameters |
| **Training pipeline** (`CustomTrainingJob` in the SDK) | Runs a custom or tuning job and can **upload the resulting model to Model Registry**; can use a managed dataset |

Each job has **worker pools** (see the hardware lesson for distributed roles): pool 0 = primary/chief,
pool 1 = workers, pool 2 = parameter servers or Reduction Server, pool 3 = evaluators. Vertex AI sets
`CLUSTER_SPEC` on every replica and `TF_CONFIG` for distributed TensorFlow jobs.

## Cost: Spot VMs and right-sizing

- **Spot VMs** (`scheduling strategy = SPOT`): much cheaper, but can be preempted. On preemption the job
  fails with a stockout-type error and is retried (up to six times); queued/preempted time isn't billed.
  Make training **fault tolerant**: save **checkpoints** to Cloud Storage regularly and resume from the
  latest one. Not supported for TPU Pods.
- Choose machine types/accelerators that match the bottleneck (see hardware lesson); stop idle notebooks
  and use jobs instead.

## Troubleshooting training failures

| Symptom | Likely cause → fix |
|---|---|
| Out-of-memory (OOM) on GPU | Batch too large / model too big → smaller batch, mixed precision, gradient accumulation, bigger GPU, model parallelism |
| Loss is NaN / explodes | Learning rate too high, bad inputs (NaN/inf), no normalisation → lower LR, gradient clipping, clean & scale data |
| Loss doesn't decrease | LR too low/high, bugs in labels, frozen layers, wrong loss for the task |
| Training slow, GPU underused | **Input pipeline bottleneck** → `tf.data` prefetch/parallel map/cache, TFRecords, more CPU |
| Permission errors | Training service account lacks access to bucket / BigQuery dataset |
| Job fails after preemption | Spot VM without checkpointing |
| Works locally, fails in Vertex AI | Missing dependency in container, wrong region, paths not under `/gcs/` or `AIP_*` dirs |

Use Cloud Logging for job logs and Vertex AI TensorBoard / the profiler for performance.

## Hyperparameter tuning

Define the **search space** (double, integer, categorical, discrete parameters; linear, log or
reverse-log scaling; conditional parameters) and a **metric** with a goal (maximise/minimise). Your code
reports the metric with the **`cloudml-hypertune`** library; hyperparameters arrive as command-line
arguments with matching names.

Algorithms:

| Algorithm | When |
|---|---|
| **Default (Bayesian optimisation)** — Vertex AI chooses between Gaussian-process bandits, linear combination search and variants | Best general choice; learns from earlier trials |
| **Grid search** | All parameters discrete/categorical/integer and the grid is small enough to try exhaustively |
| **Random search** | Many parallel trials, simple baseline |

Trade-offs to remember:
- **Parallel trials** finish faster, but Bayesian optimisation learns less between trials — very high
  parallelism makes it behave closer to random search.
- **Early stopping** of unpromising trials saves cost.
- More hyperparameters → more trials needed → more cost (billed per trial duration).
- Use **log scale** for learning rate / regularisation strengths spanning orders of magnitude.
- Vertex AI Vizier is the underlying black-box optimisation service, also usable directly for non-ML
  optimisation problems.

## ⚖️ Prebuilt vs custom container

| Situation | Choose |
|---|---|
| TensorFlow 2.x / PyTorch / sklearn / XGBoost, standard deps | Prebuilt |
| R, Java, C++ code; system libraries; private packages | Custom |
| Need identical environment in training and serving / reproducible builds | Custom (pinned image) |
| Fastest path from a notebook script | Prebuilt (or autopackaging from the SDK/CLI) |

## ⚖️ Bayesian vs grid vs random

| | Bayesian (default) | Grid | Random |
|---|---|---|---|
| Uses previous results | Yes | No | No |
| Efficient with few trials | **Best** | Poor | OK |
| Parallel-friendly | Less | Yes | **Best** |
| Parameter types | Any | Discrete only | Any |

## 🪤 Exam traps

- **Spot VMs without checkpoints** — cheap until preemption wipes progress.
- **Grid search over continuous ranges** — not supported; grid needs discrete values.
- **Massive parallel trials with Bayesian search** to "save time" — reduces search quality.
- **Building a custom container** when a prebuilt one covers the framework — extra maintenance.
- **Reporting the wrong metric** (training loss instead of validation metric) to the tuner → overfitting.
- **Model not in the Registry** after a bare CustomJob — use a training pipeline or upload the model.

## ✅ Key takeaways

- Prebuilt container for standard frameworks; custom container for anything else or full reproducibility.
- CustomJob runs code; training pipelines also register the model; HyperparameterTuningJob runs trials.
- Spot VMs + checkpoints for cheap, fault-tolerant training.
- Hyperparameter tuning: Bayesian default, report metric via hypertune, mind parallelism vs quality.
