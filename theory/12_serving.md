Serving is the largest single area of the exam (~20 %). You need to choose **online vs batch**, the
right **endpoint type**, **hardware and scaling**, how to **roll out** new versions safely, and where to
put **pre/post-processing**.

## Online vs batch prediction

| | **Online prediction** | **Batch prediction** |
|---|---|---|
| How | Synchronous request to an **endpoint** with the model **deployed** on nodes | Asynchronous `BatchPredictionJob` against a model in the **Model Registry** — **no endpoint needed** |
| Latency | Milliseconds–seconds per request | Minutes–hours for the whole job |
| Cost model | Pay for deployed nodes while they run (min replicas ≥ 1 typical) | Pay only while the job runs |
| Use when | User-facing apps, real-time decisions | Scoring tables/files periodically, nightly recommendations, large backfills |

Batch prediction details: input from **JSON Lines, TFRecord, CSV, file lists in Cloud Storage or a
BigQuery table**; output to Cloud Storage (JSONL) or **BigQuery**. Input, output and model must be in the
same region. It doesn't autoscale — set `starting_replica_count`; each replica takes minutes to start, so
very small jobs are inefficient. Feature attributions can be requested in batch too.

## Endpoint types (Vertex AI)

| Endpoint | Key properties | Choose when |
|---|---|---|
| **Dedicated public endpoint** *(recommended default)* | Dedicated networking, up to 1 h timeout, 10 MB payloads, HTTP + gRPC, **streaming**, traffic split, request/response logging; no VPC-SC | Public apps, LLM streaming, large payloads |
| **Shared public endpoint** | 60 s timeout, 1.5 MB payload, HTTP only, VPC-SC supported; needed for tuned Gemini and AutoML / explanations | Classic default; AutoML models; VPC-SC perimeter with public endpoint |
| **Dedicated private endpoint via Private Service Connect** *(recommended for production private traffic)* | Private, up to 1 h timeout, 10 MB, HTTP + gRPC, streaming, traffic split, logging, VPC-SC | Traffic must stay inside your network, enterprise/regulated workloads |
| **Private endpoint via VPC Network Peering** (older) | 60 s, 10 MB, HTTP only, **no traffic split, no logging** | Legacy private setups |

## Scaling and hardware

- Deploy with **machine type**, optional **accelerators**, **min and max replicas**; autoscaling adds
  nodes based on utilisation targets (CPU by default, ~60 %; GPU duty cycle for GPU models).
- Min replicas > 0 keeps latency predictable (no cold starts); max replicas caps cost.
- **Model co-hosting** (*deployment resource pools*): several models share the same VMs — great for
  many small, low-traffic models. Limits: prebuilt TensorFlow (GA) / PyTorch (preview) containers with
  the same image and version; no custom containers, AutoML or Explainable AI; models aren't isolated.
- **Optimized TensorFlow runtime**: drop-in prebuilt container (`tf_opt-*`) with faster, cheaper
  inference — optional XLA pre-compilation and model compression, GPU acceleration for tabular Keras
  models; no extra charge.
- Reduce latency/cost: smaller/distilled/quantised models, batching requests, GPUs for large deep
  models, CPUs for trees/small models, co-locate endpoint with callers.

## Containers and pre/post-processing

| Option | Use |
|---|---|
| **Prebuilt prediction containers** | TensorFlow, PyTorch, scikit-learn, XGBoost models saved in the expected format |
| **Custom prediction routines (CPR)** | Add Python **pre/post-processing** around a model without writing a web server |
| **Custom container** | Any framework/server (e.g. vLLM, Triton), full control; must expose health and predict routes |
| Preprocessing inside the model | Keras preprocessing layers / tf.Transform graph — removes skew |

## Where else models are served

| Platform | When |
|---|---|
| **Vertex AI endpoints** | Managed default: autoscaling, monitoring, traffic split, explanations |
| **Cloud Run** | Serverless containers (incl. GPUs), scale to zero; good for lightweight or spiky inference, custom APIs |
| **GKE** | Full control, existing Kubernetes platform, custom serving stacks, multi-model GPU sharing |
| **BigQuery ML** | In-warehouse batch scoring with SQL |
| **Edge / on-device** | TF Lite (quantised) on mobile/IoT — offline, low latency, privacy |

## Rollouts: comparing model versions safely

- **Traffic splitting** on one endpoint: deploy the new model next to the old one and send e.g.
  **5–10 % (canary)**, watch metrics, then shift gradually. Rollback = move traffic back.
- **A/B testing**: split traffic between versions and compare *business* metrics with statistical
  significance.
- **Shadow (dark) deployment**: send copies of traffic to the new model without returning its responses.
- **Model Registry aliases** (`default`, `champion`, `challenger`) decouple clients from version numbers.
- Traffic split is supported on dedicated public, shared public and PSC endpoints — not on VPC-peering
  private endpoints.

## Latency budget: where the milliseconds go

End-to-end latency = network + **feature lookup** + preprocessing + **model inference** + postprocessing.
Fix the biggest slice first:

| Slice | Levers |
|---|---|
| Network | Co-locate endpoint with callers (same region), private connectivity, gRPC, keep-alive |
| Feature lookup | Precompute features; Bigtable / Feature Store online serving instead of BigQuery queries |
| Preprocessing | Move it into the model graph (avoids extra hops), vectorise |
| Inference | Smaller/distilled/quantised model, GPU for large deep models, optimised runtime (Optimized TF runtime, TensorRT, vLLM), batching |
| Cold starts | Min replicas ≥ 1; pre-warm before known spikes |

## Requests and payloads

- Online requests send `instances` (JSON) — images as **base64**. For large inputs, send a **Cloud
  Storage URI** and let the model read it, or use a dedicated endpoint (10 MB limit vs 1.5 MB shared).
- Batch prediction reads files/tables directly — use it for large volumes.
- Ask for **explanations** per request (`explain`) only when needed: they cost extra latency.

## Serving open LLMs

Deploy from Model Garden to a Vertex AI endpoint with an optimised server: **vLLM** (GPUs, continuous
batching, paged attention), **Hex-LLM** (TPUs), or a custom container (e.g. Triton, TGI). Key levers:
**quantisation** (int8/int4) to fit smaller/fewer GPUs, maximum context length (KV cache memory),
autoscaling on GPU duty cycle, and **streaming** responses (needs a dedicated endpoint).

## Autoscaling details

- Autoscaling reacts to utilisation (CPU, GPU duty cycle; request-based metrics on newer options) with a
  delay of minutes — for sudden, predictable spikes raise **min replicas** beforehand.
- Standard endpoints keep at least one replica running; if near-zero traffic must cost ~nothing, consider
  **Cloud Run** (scale to zero), co-hosting, or batch.

## ⚖️ Online vs batch — quick decisions

| Scenario | Answer |
|---|---|
| Score 50 M customers nightly into BigQuery | Batch prediction (BigQuery in/out) |
| Fraud check during checkout | Online endpoint |
| Recommendations refreshed daily, read by app from a DB | Batch → write to Bigtable/Firestore |
| Spiky low traffic, cost matters most | Cloud Run (scale to zero) or co-hosting |
| Many small models, little traffic each | Model co-hosting |

## ⚖️ Endpoint choice

| Requirement | Endpoint |
|---|---|
| Must not traverse the public internet | PSC dedicated private endpoint |
| Streaming LLM tokens / requests > 1.5 MB / long timeouts | Dedicated (public or PSC) |
| AutoML model or tuned Gemini | Shared public |
| Need canary rollout | Any except VPC-peering private |

## 🧪 Worked scenarios

### 1. Score 100 M rows nightly
Every night, churn scores must be computed for 100 M customers stored in BigQuery.

**Answer:** **Batch prediction** with BigQuery input and output (or BigQuery ML `ML.PREDICT` if the model
is a BQML model). No endpoint.

### 2. Risky new model
A retrained recommendation model looks better offline; the team fears a revenue drop.

**Answer:** Deploy next to the current model on the same endpoint with a **10 % traffic split (canary)**,
compare business metrics, then shift traffic gradually (or A/B test with significance).

### 3. 50 tiny regional models
Fifty small TensorFlow models, one per region, each receiving a few requests per minute.

**Answer:** **Model co-hosting** with a deployment resource pool (or Cloud Run) — not 50 separately sized
endpoints.

### 4. 8 MB images, token streaming
A multimodal app sends 8 MB images and needs streamed responses.

**Answer:** A **dedicated endpoint** (public or PSC) — shared public endpoints are limited to 1.5 MB and
don't stream. Alternatively upload images to Cloud Storage and pass URIs.

### 5. Traffic must stay private, with canary rollouts
A bank's internal apps call the model; nothing may traverse the public internet and they need traffic
splitting and request logging.

**Answer:** **Dedicated private endpoint via Private Service Connect** — VPC-peering private endpoints
lack traffic split and logging.

## 🪤 Exam traps

- **Deploying to an endpoint just to run batch scoring** — batch prediction doesn't need an endpoint.
- **Online endpoint for nightly jobs** — paying for idle nodes.
- **Switching 100 % traffic at once** — use traffic split/canary.
- **Doing preprocessing in the client app differently from training** — CPR, in-model preprocessing or
  Feature Store.
- **Expecting batch jobs to autoscale** — set replica counts.
- **VPC-peering private endpoint + traffic split/logging** — not supported; use PSC.
- **Querying BigQuery inside the online request path** for features — seconds of latency; use an online
  store.
- **Base64-encoding huge files into online requests** — use Cloud Storage URIs or batch prediction.

## ✅ Key takeaways

- Online = endpoint + deployed nodes; batch = job on a registered model, no endpoint.
- Dedicated public (default) / PSC private (production private) / shared public (AutoML, tuned Gemini).
- Scale with min/max replicas; co-host small models; Optimized TF runtime for TF models.
- Roll out with traffic split (canary, A/B) and Model Registry aliases.
