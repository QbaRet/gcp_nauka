Models decay because the world changes. The exam expects you to tell **training-serving skew**, **data
drift**, **concept drift** and **feature attribution drift** apart, to configure **Vertex AI Model
Monitoring**, and to know what to do when an alert fires.

## The four problems

| Problem | What changed | Compared against | Typical cause |
|---|---|---|---|
| **Training-serving skew** | Production inputs differ from **training data** | Training dataset (baseline) | Different preprocessing in serving, bug, stale features, training sample unrepresentative |
| **Data (prediction/inference) drift** | Production inputs change **over time** | Earlier production data | Seasonality, new user segments, market change |
| **Concept drift** | The relationship **inputs → label** changes | Ground-truth labels | Fraudsters adapt, customer behaviour changes |
| **Feature attribution drift** | Which features the model *relies on* changes | Baseline attributions | Upstream data issue, shifting importance |

Skew and drift can be detected **without labels** (input distributions only). Concept drift needs
**ground truth** — monitor model quality metrics when labels arrive (often delayed).

## Vertex AI Model Monitoring

### v1 (GA, attached to endpoints)
- Enable on a Vertex AI **endpoint** (or batch prediction). Choose **skew detection** (needs the
  **training data** in Cloud Storage or BigQuery) and/or **drift detection** (baseline = past production
  data). You can enable both.
- Distances: **L-infinity** for categorical features, **Jensen-Shannon divergence** for numerical
  features. **Threshold** per feature (default 0.3) — alert when the distance exceeds it.
- **Sampling rate** (fraction of requests logged; all if unset) and **monitoring frequency** (default
  24 h, minimum 1 h) — a trade-off between cost and detection speed.
- Alerts by **email** and **Cloud Monitoring notification channels** (e.g. Pub/Sub, Slack, PagerDuty);
  anomalies can be written to **Cloud Logging**. Settings are shared by all models on one endpoint.
- Can also monitor **feature attribution** skew/drift when explanations are configured.

### v2 (Preview, attached to model versions)
- A **model monitor** is tied to a model version in the Model Registry — works for models served on
  Vertex AI **and outside it** (register the model, define the schema, send data).
- Objectives: **input feature drift**, **output (prediction) drift**, **feature attribution** drift
  (SHAP-based); training baseline optional.
- Runs **on demand or on a schedule**. v1 keeps working; no forced migration.

### Feature Store monitoring
Feature monitors on feature groups compute statistics and drift anomalies for features over time.

## Logging and other signals

- **Request-response logging** on endpoints (to BigQuery) gives you the raw data to analyse, label later
  and compute real quality metrics.
- Cloud Monitoring/Logging for latency, error rates, CPU/GPU utilisation, replica counts.
- BigQuery ML: `ML.VALIDATE_DATA_SKEW` / `ML.VALIDATE_DATA_DRIFT`; TFDV in TFX pipelines.

## What to do when an alert fires

1. **Check for bugs first** — skew is often a preprocessing mismatch or broken upstream feature, not
   real change. Fix the pipeline, don't retrain on broken data.
2. If the change is real: collect recent data (and labels), **retrain**, validate against the current
   model, roll out with canary.
3. Automate: alert → Pub/Sub → Cloud Run function → **retraining pipeline** with evaluation gates.
4. Tune thresholds to avoid alert fatigue; monitor the most important features.

## Monitoring generative AI

- Evaluate continuously with the **Gen AI evaluation service** (rubric-based / LLM-as-a-judge,
  computation-based metrics) on sampled production traffic.
- Track **safety** (filter/blocked rates), **groundedness**/hallucinations, latency, token usage/cost,
  user feedback.

## How the distances behave

- **L-infinity distance** (categorical): the largest absolute change in any category's share. Baseline
  `{web: 0.40, app: 0.60}`, production `{web: 0.75, app: 0.25}` → distance **0.35** → above the default
  0.3 threshold → alert.
- **Jensen-Shannon divergence** (numerical): symmetric measure between two distributions, 0 = identical,
  1 = completely different (log base 2). Values are binned first.
- Small, important features may need **lower thresholds**; noisy ones higher, to avoid alert fatigue.

## Ground truth arrives late

Concept drift and real accuracy need labels, which may arrive days or months later (loan default,
churn):

1. Log every prediction with an ID and the features (endpoint **request-response logging** to BigQuery).
2. When labels arrive, **join** them to predictions and compute metrics per time window and per slice.
3. Alert on metric drops (Cloud Monitoring on a scheduled query, or a pipeline step).
4. Until labels arrive, use **input and prediction drift** as early-warning proxies.

## Operational (service) monitoring

Besides model quality, monitor the service like any production API: **latency (p50/p95/p99)**, **error
rate** (4xx/5xx), **throughput**, **replica count**, CPU/GPU utilisation and memory. Define SLOs and alert
through Cloud Monitoring. A spike in latency with stable traffic often means a resource or dependency
problem — not drift.

## Slices and feedback loops

- Aggregate metrics can hide problems in one **slice** (country, device, new users) — monitor key slices.
- **Feedback loops**: a recommender trained on its own recommendations narrows what users see; keep some
  exploration traffic and log impressions to avoid biased training data.

## ⚖️ Skew vs drift vs concept drift

| Question says… | It's… | Detect with |
|---|---|---|
| "Serving data distribution differs from training data" | Training-serving skew | Model Monitoring skew detection (training baseline) |
| "Feature distributions changed over the last months" | Data drift | Drift detection (production baseline) |
| "Inputs look the same but accuracy dropped" | Concept drift | Ground-truth evaluation, retraining |
| "Model suddenly relies on a different feature" | Attribution drift | Attribution monitoring (needs explanations) |

## ⚖️ Monitoring configuration trade-offs

| Setting | Higher value | Lower value |
|---|---|---|
| Sampling rate | More accurate stats, higher cost | Cheaper, noisier |
| Frequency | Slower detection, cheaper | Faster detection (≥ 1 h), more cost |
| Threshold | Fewer alerts, may miss issues | Sensitive, alert fatigue |

## 🧪 Worked scenarios

### 1. Accuracy dropped, inputs unchanged
A fraud model's precision fell from 0.8 to 0.5 over two months; input distributions look stable.

**Answer:** **Concept drift** (fraud patterns changed). Retrain on recent labelled data with evaluation
gates; drift detection on inputs can't see it.

### 2. Skew right after launch
A day after deployment, skew alerts fire on "income": production values are 1 000× training values.

**Answer:** A **preprocessing bug / unit mismatch** (e.g. thousands vs units) — fix the serving pipeline,
don't retrain.

### 3. No access to the training data
A vendor-provided model is deployed; its training data isn't available, but you must watch for changes.

**Answer:** **Drift detection** (baseline = earlier production data), or Model Monitoring v2 without a
training baseline. Skew detection needs training data.

### 4. Detect faster, but cost matters
Alerts currently come daily; the business wants detection within hours without doubling cost.

**Answer:** Increase **monitoring frequency** (e.g. every 1–6 h) and lower the **sampling rate** to
offset cost, focusing on the most important features.

### 5. Automate the reaction
On a drift alert, retraining should start automatically but bad models must not reach production.

**Answer:** Alert → **Pub/Sub** → Cloud Run function → **retraining pipeline** with data validation,
champion/challenger evaluation and a canary rollout.

## 🪤 Exam traps

- **Skew detection without training data** — not possible; use drift detection instead.
- **Concept drift detected from inputs only** — needs labels / quality metrics.
- **Automatically retraining on skew caused by a bug** — fix the serving pipeline first.
- **Accuracy alone in production** — labels arrive late; use drift as an early proxy.
- **One endpoint, many models, different monitoring needs** — v1 settings are per endpoint.
- **Monitoring only the aggregate metric** — problems often hide in slices.
- **Treating latency spikes as model drift** — that's an operational issue (resources, dependencies).

## ✅ Key takeaways

- Skew = vs training data; drift = vs past production; concept drift = label relationship changed.
- Model Monitoring v1: endpoints, L-infinity / Jensen-Shannon, thresholds (0.3 default), sampling,
  frequency (default 24 h), email/Cloud Monitoring alerts.
- v2: per model version, works for models outside Vertex AI, input/output/attribution drift.
- Alert → investigate → retrain with gates → canary rollout; automate with Pub/Sub-triggered pipelines.
