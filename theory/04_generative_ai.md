Generative AI got much heavier in the newer PMLE exam guide: selecting models in **Model Garden**,
building RAG applications, **tuning** foundation models (including from BigQuery), optimising Gemini apps
for **cost, latency and availability**, and **evaluating** gen AI output (LLM-as-a-judge). The question
bank here has relatively few gen AI questions, so this lesson matters more than its question count
suggests.

## Model Garden: where models come from

Model Garden is the catalogue of models on Vertex AI:

- **Foundation models** — Google's first-party models (Gemini for text/multimodal, Imagen for images,
  Veo for video, embedding models) used as managed APIs ("models as a service"); tunable through the
  console, API or SDK.
- **Open / fine-tunable models** (Gemma, Llama, Mistral…) — deploy to your own Vertex AI endpoint
  (serving stacks such as vLLM or Hex-LLM on GPUs/TPUs) and fine-tune with notebooks or pipelines,
  billed as custom training/serving compute.
- **Task-specific solutions** — mostly ready to use, some customisable with your data.

Choosing a model: capability needed (text, multimodal, code, image generation), **quality vs cost vs
latency** (a smaller/"Flash"-class model for high-volume, latency-sensitive tasks; a larger/"Pro"-class
model for complex reasoning), context window, data-residency and licensing (open models you host
yourself give more control; managed models need no infrastructure).

## Prompting → grounding/RAG → tuning

Google's guidance: **start with prompting**, find the best prompt, and move to tuning only if needed.

1. **Prompt engineering** — clear instructions, role/system instructions, few-shot examples, output
   format (JSON schema), step-by-step reasoning. Cheapest; try first.
2. **Grounding** — anchor answers in a source to reduce hallucinations and provide citations. Options
   include grounding with **Google Search**, Google Maps, **Vertex AI Search** (now "Agent Search"),
   **RAG Engine**, Elasticsearch, or your own search API.
3. **RAG (retrieval-augmented generation)** — retrieve relevant chunks of *your* data and put them in the
   prompt. Use it for private, large or frequently changing knowledge.
4. **Tuning** — change model behaviour when prompting isn't enough.

### RAG Engine pipeline
Ingest (local files, Cloud Storage, Google Drive) → **chunk** → **embed** → **index** into a *corpus* →
**retrieve** relevant chunks for a query → **generate** the answer with retrieved context.
Chunk size/overlap and the embedding model are the main quality levers.

### Vector Search (formerly Matching Engine)
Managed approximate-nearest-neighbour search built on Google Research's **ScaNN**. Supports dense, sparse
and hybrid search, filtering with *restricts* (numeric/text attributes), and batch or streaming index
updates. Used as the retrieval layer for RAG, semantic search and recommendations over embeddings.
Recall = share of true nearest neighbours returned; tune the index for the recall/latency trade-off.

### Tuning methods for Gemini

| Method | Data | Good for |
|---|---|---|
| **Supervised fine-tuning (SFT)** | Hundreds–thousands of labelled prompt→response examples | Classification, extraction, strict output format, domain style |
| **Preference tuning** | Chosen vs rejected response pairs | Subjective quality, tone, helpfulness |
| **Reinforcement-learning fine-tuning** | Dozens–hundreds of prompts + reward functions (string match, Gemini autorater, code, Cloud Run scorer) | Verifiable tasks where you can score outputs |

**Parameter-efficient tuning** (adapters/LoRA) updates a small subset of weights — cheaper and faster;
**full fine-tuning** updates everything — potentially higher quality but more expensive to tune and
serve. Quality of examples beats quantity. BigQuery can also drive supervised tuning of Gemini through
remote models, keeping training data in the warehouse.

## Evaluating gen AI

The Gen AI evaluation service scores model outputs with:

- **Rubric-based metrics (LLM-as-a-judge)** — *adaptive rubrics* (generated per prompt, pass/fail;
  recommended) or *static rubrics* (same criteria for every prompt, e.g. a 1–5 score) for qualities like
  fluency, groundedness, instruction following, safety.
- **Computation-based metrics** — deterministic, need a reference answer: **ROUGE**, **BLEU**, exact match.
- **Custom function metrics** (Python SDK).

Evaluation datasets can come from uploaded files, sampled production logs or synthetic generation. Use
evaluation to compare prompts, models and tuned versions *before* switching production traffic.

## Cost, latency and availability of Gemini apps

- Use the **smallest model that meets quality**; route only hard requests to bigger models.
- Shorten prompts and outputs (tokens = cost and latency); set max output tokens.
- **Context caching** for large, repeated context (long documents, system prompts).
- **Batch prediction** for large offline jobs instead of many online calls.
- **Provisioned throughput** for guaranteed capacity on critical workloads; handle 429s with retries and
  exponential backoff; use multiple regions for availability.
- Stream responses to improve perceived latency.

## Generation parameters and structured output

| Parameter | Effect | Typical setting |
|---|---|---|
| **Temperature** | Randomness of token choice | ~0 for extraction/classification; higher for creative writing |
| **Top-p / top-k** | Restrict sampling to the most likely tokens | Lower = more focused |
| **Max output tokens** | Caps response length (and cost) | Set it for every production call |
| **Stop sequences** | End generation at a marker | Templated outputs |
| **Response schema** (controlled generation) | Forces valid JSON matching a schema / enum | Extraction, classification into fixed labels |
| **System instructions** | Persistent role, rules and style | Persona, safety rules, output language |

"The model sometimes returns invalid JSON" → use a **response schema** (and temperature 0) before
considering tuning.

## Embeddings

Embedding models map text (or images/video with multimodal embeddings) to vectors so that similar
meaning → nearby vectors. Uses: semantic search, RAG retrieval, clustering, deduplication,
recommendations, features for classifiers.

- Set the **task type** — e.g. `RETRIEVAL_DOCUMENT` when indexing, `RETRIEVAL_QUERY` for the query,
  `SEMANTIC_SIMILARITY`, `CLASSIFICATION`, `CLUSTERING` — it improves quality.
- You can reduce **output dimensionality** to save storage/latency at a small quality cost.
- Use the **same embedding model** for documents and queries; changing it means re-embedding everything.

## Improving RAG quality

| Problem | Lever |
|---|---|
| Right document exists but isn't retrieved | Better chunking (size/overlap, by section), **hybrid search** (dense + keyword/sparse), query rewriting, more chunks (top-k) |
| Retrieved chunks are noisy | **Re-ranking** (Vertex AI ranking API), metadata **filters** (product, date, language) |
| Answer ignores the context / hallucinates | Instruct "answer only from context, else say you don't know", check **groundedness** |
| Stale answers | Incremental re-indexing when documents change |

Evaluate **retrieval** (recall@k, does the right chunk appear?) separately from **generation**
(groundedness, answer quality) — otherwise you can't tell which half to fix.

## Agents and function calling

**Function calling**: you declare tools (name, description, JSON parameters); the model returns a
*structured call* and **your code executes it** and returns the result to the model. This is how LLMs
query databases, call APIs or take actions. **Agents** loop over reason → call tool → observe. On Google
Cloud they are built with the **Agent Development Kit (ADK)** or frameworks such as LangChain/LangGraph,
deployed to **Agent Engine**, and grounded with Search/RAG. Security rule: give tools least privilege and
validate their inputs — the model's output is untrusted.

## ⚖️ Prompting vs RAG vs fine-tuning

| | Prompting | RAG / grounding | Fine-tuning |
|---|---|---|---|
| Adds new / private knowledge | No | **Yes** (fresh at query time) | Poorly, goes stale |
| Changes style / format / behaviour | Somewhat | No | **Yes** |
| Cost to set up | Lowest | Medium (pipeline, index) | Highest (data, tuning, serving) |
| Update when data changes | Edit prompt | Re-index documents | Re-tune |
| Citations / traceability | No | **Yes** | No |

## ⚖️ Managed Gemini vs open model you deploy

| | Gemini (managed) | Open model from Model Garden |
|---|---|---|
| Infrastructure | None | Your endpoint, GPUs/TPUs |
| Control over weights | Tuning via managed service | Full (any fine-tuning method) |
| Scaling | Google-managed quotas / provisioned throughput | You size replicas and autoscaling |
| Typical reason | Fast, high quality, low ops | Data control, custom fine-tuning, licence/cost at scale |

## 🧪 Worked scenarios

### 1. Extract fields from emails
You need order number, date and amount as JSON from customer emails; the model sometimes adds prose or
malformed JSON.

**Answer:** Use a **response schema** (controlled generation) with temperature 0 and a few-shot prompt.
Tune only if accuracy is still insufficient after prompting.

### 2. Chatbot invents prices
A shopping assistant quotes wrong prices that change daily.

**Answer:** **Ground / RAG** on the live catalogue (or call a pricing API via **function calling**).
Fine-tuning can't keep up with daily changes.

### 3. Cost of 50 M classifications per day
A Pro-class model classifies support tickets; the bill is too high and latency doesn't matter overnight.

**Answer:** Evaluate a **smaller Flash-class model** on the task, shorten prompts, use **batch
prediction** for the offline volume and **context caching** for a long shared system prompt.

### 4. Brand voice
Even with good few-shot examples, marketing copy doesn't match the company's tone, and you have 2 000
approved examples.

**Answer:** **Supervised fine-tuning** (parameter-efficient) on the approved examples; if you have
"better vs worse" pairs, **preference tuning**. Evaluate against the base model with rubric metrics.

### 5. Search 200 M product vectors with category filters
Low-latency semantic search over product embeddings, filtered by category and price.

**Answer:** **Vector Search** index with **restricts** (category) and numeric restricts (price).

## 🪤 Exam traps

- **Fine-tuning to add facts.** Up-to-date or private knowledge → RAG/grounding, not tuning.
- **Skipping prompting.** If a few-shot prompt solves it, tuning is over-engineering.
- **AutoML Text** for text classification is retired; today's answer is Gemini prompting/tuning.
- **Evaluating with exact match only.** Open-ended generation needs rubric/LLM-as-a-judge metrics;
  ROUGE/BLEU need reference answers.
- **Security of gen AI apps** (prompt injection, data leakage) is covered in the *Security, privacy and
  responsible AI* lesson — safety filters and Model Armor.
- **Different embedding models for queries and documents** — vectors aren't comparable.
- **Tuning to fix invalid JSON** — controlled generation (response schema) solves it more cheaply.
- **Letting an agent's tools run with broad permissions** — least privilege; treat model output as
  untrusted input.

## ✅ Key takeaways

- Model Garden: managed foundation models, open models you deploy, task-specific solutions.
- Prompt → ground/RAG → tune. RAG for knowledge, tuning for behaviour.
- RAG = chunk, embed, index, retrieve, generate; Vector Search (ScaNN) is the retrieval engine.
- SFT, preference tuning and RL fine-tuning; PEFT is cheaper than full fine-tuning.
- Evaluate with rubric-based (LLM-as-a-judge) and computation-based metrics before rollout.
