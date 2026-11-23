This lesson combines three exam themes that show up as "constraints" in many scenarios: **privacy of
training data** (PII/PHI), **securing ML systems** (including gen AI threats such as prompt injection and
data exfiltration), and **responsible AI** (explainability, fairness, bias monitoring).

## Handling sensitive data: Sensitive Data Protection (formerly Cloud DLP)

| Capability | What it does |
|---|---|
| **Discovery** | Profiles data across an org/folder/project (BigQuery, Cloud SQL, Cloud Storage) to find where sensitive data lives |
| **Inspection** | Deep scan for **infoTypes** (names, emails, credit cards, national IDs, health data…) via jobs or the `content.inspect` API |
| **De-identification** | Transform sensitive values before using data for ML or analytics |
| **Risk analysis** | Re-identification risk of structured BigQuery data (e.g. **k-anonymity**) |

De-identification techniques:

| Technique | Effect | Keeps ML usefulness? |
|---|---|---|
| **Redaction / masking** | Remove or replace characters (`****-1234`) | Loses the value |
| **Tokenization / pseudonymisation** (e.g. deterministic encryption, format-preserving encryption) | Consistent surrogate token; same input → same token, optionally reversible with the key | **Yes** — joins and counts still work |
| **Bucketing / generalisation** | Age 37 → 30–40, zip → region | Yes, coarser |
| **Date shifting** | Shift dates by a random but consistent offset per person | Yes — intervals preserved |

Typical exam pattern: "train on data containing PII without exposing it" → run Sensitive Data Protection
de-identification (tokenize identifiers, bucket quasi-identifiers) in the pipeline **before** data lands
in the training dataset; keep keys in Cloud KMS. Drop columns the model doesn't need at all.

## Securing ML workloads

- **IAM least privilege**: dedicated **service accounts** for training, pipelines and endpoints with only
  the roles they need; avoid primitive roles (Owner/Editor); control who can act as a service account.
- **VPC Service Controls**: a perimeter around projects/services (BigQuery, Cloud Storage, Vertex AI)
  to prevent **data exfiltration** even with valid credentials.
- **Private networking**: private endpoints (PSC), private IP for Workbench, no public IPs.
- **CMEK** (customer-managed encryption keys in Cloud KMS) when the organisation must control keys;
  data is encrypted at rest by default with Google-managed keys.
- **Audit logs** (Cloud Audit Logs) for who accessed data/models; Access Transparency where required.
- Health data (**PHI**) requires HIPAA-eligible services and appropriate agreements; keep data in
  compliant regions/services.

## Gen AI security

Threats: **prompt injection / jailbreaks**, **sensitive data leakage** (users pasting PII, model
revealing confidential context), **malicious URLs/content**, harmful output.

| Control | What it does |
|---|---|
| **Safety filters** (Gemini) | Score content on four harm categories — **hate speech, harassment, sexually explicit, dangerous content** — by probability and severity; you set a **blocking threshold** per category (`BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_ONLY_HIGH`, `BLOCK_NONE`, `OFF`). Separate, **non-configurable** filters always block CSAM and sensitive PII; a citation (recitation) filter is separate too |
| **Model Armor** | Screens **prompts and responses** of AI apps (on Google Cloud or other clouds): prompt-injection & jailbreak detection, sensitive data detection/redaction via Sensitive Data Protection, malicious URL detection, responsible-AI content filters, CSAM detection. Configured with **templates** (filters + confidence thresholds); **floor settings** enforce minimum protections for all templates in a project |
| **Regex / allow-lists / output validation** | Deterministic checks on inputs/outputs (e.g. block account numbers) |
| **Grounding + least-privilege tools** | Limit what the model can see and do; don't put secrets in prompts |
| **VPC-SC, IAM, logging** | Same platform controls as for classic ML |

Recommended process: assess risks → test safety (red-teaming) → configure filters → monitor user feedback.

## Explainability

Why: debugging, trust, regulation (e.g. explain credit decisions), detecting reliance on proxy features.

**Vertex Explainable AI** feature attributions:

| Method | Use with | Notes |
|---|---|---|
| **Sampled Shapley** | **Non-differentiable** models (tree ensembles, any custom model), AutoML tabular | Approximates Shapley values by sampling feature permutations (`pathCount`, ~25) |
| **Integrated Gradients** | **Differentiable** models (neural nets), large feature spaces, low-contrast images (X-rays) | Integrates gradients from a **baseline** (`stepCount`, ~50) |
| **XRAI** | **Images**, especially natural images with several objects | Builds on IG, highlights *regions* |
| Example-based explanations | TensorFlow models producing embeddings | Nearest neighbours from the training set; not for trees |

Configure an `explanationSpec` (method + metadata/baselines) at upload, deploy, batch job or per request.
Attributions are relative to a **baseline** (default all-zeros / black image) and should sum to the
prediction minus the baseline prediction.

**Status:** Vertex Explainable AI was **deprecated on March 16, 2026** (access ends on/after March 16,
2027); Google suggests open-source **SHAP** and **LIME** as alternatives. The exam guide still lists
model explainability, and the concepts (Shapley vs gradients, baselines, local vs global) are what's
tested. BigQuery ML keeps its own explainability (`ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN`).

**Local vs global**: local = why *this* prediction (per-instance attributions); global = which features
matter overall (aggregated attributions, feature importance). Interpretable-by-design models (linear,
small trees) are an alternative when regulations demand transparency.

## Fairness and bias

- Sources of bias: unrepresentative sampling, historical bias in labels, proxy features (zip code ≈
  ethnicity), measurement bias, feedback loops.
- **Evaluate metrics per slice** (gender, age group, region) — e.g. TensorFlow Model Analysis /
  **Fairness Indicators**, What-If Tool; compare false positive/negative rates across groups.
- Mitigation: collect more representative data, re-weight/re-sample, remove or audit proxy features,
  adjust thresholds per group where legally appropriate, monitor fairness in production.
- Document with **model cards** (intended use, limitations, evaluation per slice).
- Removing a sensitive attribute alone doesn't remove bias if proxies remain.

## Fairness metrics

| Metric | Requires equal across groups… | Use when |
|---|---|---|
| **Demographic parity** | Positive prediction rate | Outcomes (e.g. offers) should be distributed equally |
| **Equal opportunity** | True positive rate (recall) | Qualified people must have the same chance of a positive decision |
| **Equalized odds** | TPR **and** FPR | Both missed and false positives matter (e.g. justice, lending) |
| **Predictive parity** | Precision | A positive prediction must mean the same thing for everyone |

When base rates differ between groups these criteria **cannot all hold at once** — the choice is a
business/ethical decision to document in the model card. Measure them per slice (Fairness Indicators /
TFMA, What-If Tool, BigQuery queries on predictions).

## Privacy-enhancing techniques

- **Differential privacy** — adds calibrated noise so no individual's presence can be inferred. In
  training: **DP-SGD** (TensorFlow Privacy, Opacus); in analytics: BigQuery
  `SELECT WITH DIFFERENTIAL_PRIVACY` for aggregates. Trade-off: privacy budget (epsilon) vs accuracy.
- **Federated learning** — train on devices; only model updates leave the device (keyboard prediction,
  mobile personalisation).
- **Data minimisation** — collect and keep only the features the model needs; set retention.
- **Confidential computing** — encrypt data in use (Confidential VMs / Confidential GKE nodes, Workbench
  Confidential Computing).

## Responsible AI lifecycle

1. **Define** intended use, users and harms; check against Google's AI Principles / your policy.
2. **Data**: representativeness, consent, labelling quality, **data cards**.
3. **Model**: evaluation per slice, explainability, red-teaming for gen AI.
4. **Document**: **model cards** (intended use, limitations, metrics per slice, ethical considerations).
5. **Deploy & monitor**: fairness and safety in production, user feedback, human oversight for
   high-stakes decisions.

## ⚖️ Which explanation method?

| Model | Method |
|---|---|
| Boosted trees / random forest / any black box | Sampled Shapley (or SHAP/LIME) |
| Neural network on tabular/text | Integrated Gradients |
| Image classifier, "which regions mattered" | XRAI (or IG for low-contrast images) |
| "Show similar training examples" | Example-based |
| BigQuery ML model | `ML.EXPLAIN_PREDICT` / `ML.GLOBAL_EXPLAIN` |

## ⚖️ Privacy technique by requirement

| Requirement | Technique |
|---|---|
| Must join on customer ID without seeing it | Deterministic tokenization / FPE |
| Show only last 4 digits | Masking |
| Keep age signal, reduce re-identification | Bucketing |
| Preserve time between events per patient | Date shifting |
| Prove data can't be re-identified | Risk analysis (k-anonymity) |
| Stop data leaving the project even with leaked credentials | VPC Service Controls |
| Organisation controls encryption keys | CMEK |

## 🧪 Worked scenarios

### 1. Loan model and zip code
A loan model doesn't use ethnicity, but approval rates differ sharply by ethnic group; zip code is a top
feature.

**Answer:** Zip code is a **proxy**. Evaluate fairness metrics **per slice**, audit/remove or coarsen the
proxy, re-weight data, consider per-group thresholds where legal, and document in the model card.

### 2. Train on PII
Data scientists need to train a churn model on customer records containing names, emails and birth
dates, without seeing them.

**Answer:** **Sensitive Data Protection de-identification** in the ingestion pipeline: drop names,
**tokenize** customer IDs/emails (deterministic, key in Cloud KMS), **bucket** birth dates into age bands.

### 3. Explaining a boosted-tree credit model
Regulators require per-decision explanations for an XGBoost model.

**Answer:** **Sampled Shapley** (or open-source **SHAP** TreeExplainer) — Integrated Gradients needs a
differentiable model.

### 4. Prompt injection in a support bot
Users paste text instructing the bot to reveal internal discount codes from its context.

**Answer:** **Model Armor** (prompt-injection/jailbreak and sensitive-data filters) on inputs and
outputs, don't put secrets in the prompt, least-privilege tools, plus safety settings.

### 5. Exfiltration with stolen credentials
Security wants training data in BigQuery to be unusable outside the corporate perimeter even if a key
leaks.

**Answer:** **VPC Service Controls** perimeter (plus least-privilege IAM and no long-lived keys).

## 🪤 Exam traps

- **Dropping the sensitive column** doesn't fix bias when proxies remain, and masking destroys features
  the model needs — tokenization/bucketing keep utility.
- **Integrated Gradients for tree models** — not differentiable; use Sampled Shapley.
- **Overall accuracy looks fine** — bias hides in slices; evaluate per group.
- **Primitive Editor role for a pipeline service account** — use least-privilege custom/predefined roles.
- **Relying only on safety filters for prompt injection** — Model Armor / input screening and limited
  tool permissions.
- **Expecting all fairness metrics to be satisfied at once** — with different base rates they conflict;
  pick and justify one.
- **Masking IDs needed for joins** — use deterministic tokenization instead.

## ✅ Key takeaways

- Sensitive Data Protection: discover, inspect, de-identify (mask, tokenize, bucket, date-shift), risk.
- Defence in depth: IAM least privilege, VPC-SC, private endpoints, CMEK, audit logs.
- Gen AI: safety filters (harm categories/thresholds) + Model Armor (prompt injection, sensitive data).
- Sampled Shapley for non-differentiable, Integrated Gradients for differentiable, XRAI for images;
  Vertex XAI is deprecated (Mar 2026) in favour of SHAP/LIME.
- Fairness = evaluate per slice, fix data, document with model cards.
