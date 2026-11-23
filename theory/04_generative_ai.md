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

## 🪤 Exam traps

- **Fine-tuning to add facts.** Up-to-date or private knowledge → RAG/grounding, not tuning.
- **Skipping prompting.** If a few-shot prompt solves it, tuning is over-engineering.
- **AutoML Text** for text classification is retired; today's answer is Gemini prompting/tuning.
- **Evaluating with exact match only.** Open-ended generation needs rubric/LLM-as-a-judge metrics;
  ROUGE/BLEU need reference answers.
- **Security of gen AI apps** (prompt injection, data leakage) is covered in the *Security, privacy and
  responsible AI* lesson — safety filters and Model Armor.

## ✅ Key takeaways

- Model Garden: managed foundation models, open models you deploy, task-specific solutions.
- Prompt → ground/RAG → tune. RAG for knowledge, tuning for behaviour.
- RAG = chunk, embed, index, retrieve, generate; Vector Search (ScaNN) is the retrieval engine.
- SFT, preference tuning and RL fine-tuning; PEFT is cheaper than full fine-tuning.
- Evaluate with rubric-based (LLM-as-a-judge) and computation-based metrics before rollout.
