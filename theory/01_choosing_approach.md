Almost every PMLE scenario starts with the same hidden question: **how much ML do you actually need to build?**
Google's answer is consistent across the exam — pick the *least custom* option that meets the requirements,
because it is faster to deliver, cheaper to operate and easier to maintain. Read every question for the
constraints that push you up the ladder: data that's unusual, accuracy targets an API can't hit, a team
without ML experts, latency, cost, or explainability.

## The ladder of options

From least to most effort:

1. **Pre-trained AI APIs** (Vision, Natural Language, Translation, Speech-to-Text, Document AI…).
   No training data, no ML expertise. You send a request, you get a prediction.
   *Use when* the task is generic (OCR, label detection, sentiment, translation) and your data
   looks like everyone else's.
2. **Foundation models from Model Garden** (Gemini, Imagen, open models such as Llama/Gemma), used with
   **prompting**, then **grounding / RAG**, and only then **tuning**. *Use when* the task is language/vision
   reasoning, generation, summarisation, extraction from free text — and when AutoML Text would have been
   the answer a few years ago (AutoML Text was retired; Google points to Gemini prompting and tuning instead).
3. **BigQuery ML** — train with SQL where the data already lives (linear/logistic regression, boosted trees,
   k-means, matrix factorization, ARIMA_PLUS forecasting, DNNs, AutoML, imported TF/ONNX/XGBoost models,
   remote models). *Use when* data is in BigQuery and the team knows SQL; avoids moving data.
4. **AutoML on Vertex AI** — you bring labelled data, Google searches architectures and hyperparameters.
   Currently supported objectives: **image classification, image object detection, tabular
   classification/regression and tabular forecasting**. *Use when* you need a custom model on your own
   labels with minimal ML code and a reasonable budget.
5. **Custom training on Vertex AI** — your own code (TensorFlow, PyTorch, scikit-learn, XGBoost, JAX) in
   prebuilt or custom containers, any architecture, distributed training, GPUs/TPUs.
   *Use when* you need full control: special architectures, custom losses, very large data, or performance
   beyond AutoML.

> The exam rewards choosing the lowest rung that satisfies **all** stated constraints. "Highest accuracy
> possible" alone rarely justifies jumping to custom training if AutoML or BigQuery ML is mentioned as
> an option and the team lacks ML expertise.

## Reading the scenario: signals and what they imply

| Signal in the question | Usually points to |
|---|---|
| "no ML expertise", "quickly", "minimal code", "prototype" | Pre-trained API → AutoML → BigQuery ML |
| Data already in **BigQuery**, analysts know **SQL** | BigQuery ML |
| Generic task (OCR, translation, sentiment, landmark/label detection) | Pre-trained API |
| Invoices, forms, contracts, receipts | Document AI processors |
| Product recommendations for retail / e-commerce | Recommendations (Retail API / commerce search) |
| Text generation, summarisation, chat, Q&A over documents | Gemini + RAG / grounding |
| Custom labels on images, tabular prediction with little ML staff | AutoML |
| Custom architecture, custom loss, research code, huge data | Custom training |
| "Must run on device / offline" | Edge-exportable model (e.g. TF Lite) |
| Strict interpretability requirements (regulated domain) | Simpler, interpretable models (linear, trees) + explanations |

## Framing the problem before picking a product

Before any product choice, the exam expects you to translate the business ask into an ML task — and to
notice when ML isn't needed at all.

| Business question | ML framing | Typical output |
|---|---|---|
| "Will this customer leave?" | Binary classification | Probability + threshold |
| "How many units will we sell next week?" | Regression / time-series forecasting | Number (with interval) |
| "Which 10 products should we show?" | Ranking / recommendation | Ordered list |
| "Which customers are similar?" | Clustering / embeddings | Segment ID / vector |
| "Is this transaction unusual?" | Anomaly detection (often unsupervised) | Score |
| "Summarise / answer / draft this" | Generative AI | Text, JSON |

**When not to use ML:** the logic is a stable, explainable rule ("flag orders > 10 000 EUR"), there is no
data or no feedback signal, errors are unacceptable and must be deterministic, or a simple heuristic is
already good enough. Google's *Rules of ML* start with "don't be afraid to launch a product without ML" —
build a heuristic baseline first and measure ML against it.

## Requirements checklist

Read the scenario for each of these; one of them usually decides the answer:

- **Success metric** — business KPI (revenue, churn) and the ML metric that proxies it (recall, RMSE).
- **Data** — where it lives (BigQuery? GCS?), volume, labels available, how fresh it must be.
- **Latency & throughput** — real-time request path vs nightly batch; QPS.
- **Team skills** — SQL analysts, no ML team, or ML engineers.
- **Time & budget** — "quickly", "prototype", "minimise cost".
- **Compliance** — PII, data residency, explainability, auditability.
- **Deployment target** — cloud endpoint, warehouse, mobile/edge, offline.
- **Operations** — "minimal operational overhead" strongly favours managed services.

## ⚖️ Pre-trained API vs AutoML vs BigQuery ML vs custom training

| | Pre-trained API | AutoML | BigQuery ML | Custom training |
|---|---|---|---|---|
| Training data needed | None | Labelled, your data | Table in BigQuery | Yours, any format |
| ML expertise | None | Low | Low–medium (SQL) | High |
| Model control | None | Low (objective, budget) | Medium (model type, options) | Full |
| Time to first model | Minutes | Hours | Hours | Days–weeks |
| Typical data | Images, text, audio, docs | Image, tabular | Tabular, time series | Anything |
| Serving | Google's API | Vertex AI endpoint / batch | SQL `ML.PREDICT`, or register to Vertex AI | Vertex AI endpoint, batch, GKE, Cloud Run |

## ⚖️ Prompting vs RAG vs tuning (foundation models)

| Need | Start with |
|---|---|
| Model knows the domain, you need a format/behaviour | **Prompt engineering** (instructions, few-shot examples) |
| Answers must use **your** up-to-date or private documents, with citations | **Grounding / RAG** (Vertex AI Search, RAG Engine, Vector Search) |
| Consistent style, classification/extraction format, domain jargon the model keeps missing | **Supervised fine-tuning** (hundreds–thousands of examples) |
| Subjective quality / tone preferences | **Preference tuning** on chosen-vs-rejected pairs |

Google's documented order: *start with prompting to find the optimal prompt, then move on to tuning if
required.* Tuning does **not** teach the model fresh facts reliably — that's what RAG is for.

## 🧪 Worked scenarios

### 1. Shelf photos
A retailer wants to read price labels from photos of store shelves taken by employees. They have no ML
team and want a solution this month. What do you use?

**Answer:** Cloud Vision API **text detection** (OCR). The task is generic, no labels are needed and the
team has no ML skills — training AutoML or a custom OCR model would be over-engineering.

### 2. Loan default in the warehouse
A bank's analysts know SQL; all loan history is in BigQuery. Regulators require an explanation for each
decision. What's the best first approach?

**Answer:** **BigQuery ML** — logistic regression or boosted trees — with `ML.EXPLAIN_PREDICT` for
per-row attributions. No data movement, analysts own it, and explainability is built in.

### 3. Defects specific to the factory
A manufacturer has 8 000 labelled images of *its own* part defects (12 defect types) and two software
engineers without ML experience. What fits?

**Answer:** **AutoML image classification** (or object detection if defects must be located). Labels are
business-specific, so the Vision API's generic labels won't work; custom training needs ML expertise the
team lacks.

### 4. Policy chatbot
HR wants an assistant that answers employee questions from internal policy PDFs that change every week,
with links to the source. What do you build?

**Answer:** **Gemini with grounding / RAG** (e.g. Vertex AI Search or RAG Engine over the PDFs). Fresh,
private knowledge with citations is exactly what RAG is for; fine-tuning would go stale every week and
gives no citations.

### 5. Research architecture
A research team needs a graph neural network with a custom loss on 40 TB of data. What do you use?

**Answer:** **Vertex AI custom training** (custom container if needed, distributed GPUs/TPUs). Nothing
lower on the ladder supports a custom architecture and loss.

## 🪤 Exam traps

- **Over-engineering.** A Kubeflow-on-GKE custom pipeline is rarely right when the question says "small
  team", "quickly" or "minimal operational overhead". Managed (Vertex AI) beats self-managed (GKE,
  Compute Engine) unless a constraint demands control.
- **Moving data unnecessarily.** If the data is in BigQuery, exporting to CSV in Cloud Storage just to
  train elsewhere is usually wrong — use BigQuery ML or read BigQuery directly from training code.
- **Old product names.** Older questions mention AutoML Natural Language, AutoML Video, AutoML Tables,
  AI Platform, or "Vertex AI Matching Engine". AutoML Tables lives on as AutoML tabular in Vertex AI;
  AutoML Text and Video are retired in favour of Gemini; Matching Engine is now Vector Search. Answer the
  question with the product it offers.
- **Vertex AI is being renamed.** Current docs call the platform *Gemini Enterprise Agent Platform*;
  the exam guide 3.1 and this question bank say *Vertex AI*. Same services.
- **Interpretability as a hard requirement** can rule out deep models even if they'd be more accurate.
- **Using ML where a rule works.** If the requirement is a fixed, explainable business rule, a rule
  engine/SQL is the right answer.
- **Ignoring the hidden constraint.** "Must work offline on a phone" or "data cannot leave the EU" can
  override every other consideration.

## ✅ Key takeaways

- Choose the least custom option that satisfies **every** constraint in the question.
- Pre-trained API → foundation model → BigQuery ML / AutoML → custom training is the escalation path.
- For gen AI: prompt → ground/RAG → tune, in that order.
- Prefer managed Vertex AI services over self-managed infrastructure unless control is explicitly needed.
