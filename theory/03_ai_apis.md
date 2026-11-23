Pre-trained APIs are Google-trained models behind a REST/gRPC API. You don't train, tune or host anything.
On the exam they are the right answer whenever the task is **generic** and the scenario stresses speed,
low cost or no ML expertise. They are the wrong answer when your labels are specific to your business
(e.g. *your* product defects) — then you need AutoML or custom training (or a tuned foundation model).

## The APIs and what they actually do

### Cloud Vision API
Features: label detection, object localization, **text detection** (sparse text in photos, signs),
**document text detection** (dense text, handwriting, PDF/TIFF), landmark and logo detection, image
properties (dominant colours), crop hints, web entities/pages, **SafeSearch** (adult, spoof, medical,
violence, racy) and face detection (faces, landmarks, emotions likelihood — **not** face recognition /
identity).
*Custom labels* (your own classes) → AutoML image classification / object detection, not the Vision API.

### Cloud Natural Language API
`analyzeSentiment` (score −1.0…1.0 and magnitude), `analyzeEntities` (people, places, organisations…),
`analyzeEntitySentiment` (sentiment per entity), `analyzeSyntax` (tokens, parts of speech, dependency
trees), `classifyText` (content categories; needs ≥ 20 tokens). `annotateText` runs several at once.
Custom text classification / extraction used to be AutoML Natural Language — **retired**; today use
Gemini prompting or tuning.

### Translation API
Basic (simple text translation) and Advanced (batch document translation, **glossaries** for consistent
domain terms, custom models). Glossary is the answer when brand names or technical terms must translate a
fixed way.

### Speech-to-Text / Text-to-Speech
Speech-to-Text transcribes audio (streaming or batch), with model adaptation / phrase hints for domain
vocabulary; Google's large speech models are branded *Chirp*. Text-to-Speech synthesises audio.

### Video Intelligence API
Labels, shot changes, object tracking, text in video, explicit content in stored or streaming video.
(Custom video models used to be AutoML Video — retired; Google suggests Gemini video tuning.)

### Document AI
Turns unstructured documents into structured data through **processors**:

| Category | Processors |
|---|---|
| Digitise | Enterprise Document OCR (optionally with image-quality analysis) |
| Extract | **Form Parser** (key-value pairs, tables), layout parser (chunks for RAG), **custom extractor** (build your own schema in Document AI Workbench), pre-trained **specialised processors** (invoices, receipts, IDs…, can be up-trained) |
| Classify / split | Custom classifier, custom splitter (split a multi-document PDF) |

Each processor you create gets its own prediction endpoint. Document AI is the answer for invoices, forms,
receipts, contracts and other document workflows — not plain Vision OCR, which only gives text.

### Recommendations and commerce search (Retail API)
Google's retail recommendations (formerly **Recommendations AI**, later Vertex AI Search for commerce; the
current docs present it alongside "AI Commerce Search") use your **product catalog** and **user events**
(views, add-to-cart, purchases). Recommendations and search share the same ingested catalog and events.
Typical models: *Others you may like*, *Frequently bought together*, *Recommended for you*. Data quality
of user events drives results; never cache personalised results and show them to another user.

### Dialogflow (conversational agents)
**Dialogflow CX** for large/complex agents (state machine of flows and pages), **Dialogflow ES** for small,
simple agents. **Agent Assist** gives real-time suggestions to human contact-centre agents. Modern
gen-AI agents are built with Gemini and Vertex AI Agent Builder; older questions use Dialogflow.

## Calling the APIs in practice

| Concern | What to know |
|---|---|
| **Sync vs async** | Small inputs: synchronous request. Large inputs: **asynchronous / batch** operations that read from and write to Cloud Storage — e.g. Vision `asyncBatchAnnotateFiles` for PDF/TIFF, Speech-to-Text long-running/batch recognition for long audio, Document AI batch processing, Translation batch document translation |
| **Authentication** | Service accounts from backends; never ship API keys or service-account keys inside mobile/web clients — call the API from your backend |
| **Data residency** | Many APIs offer regional endpoints (e.g. `eu-`) and Document AI processors are created in a location — pick the one compliance requires |
| **Quotas & cost** | Billed per unit (per image *per feature*, per 1 000 characters, per page, per minute of audio). Request only the features you need |
| **Confidence** | Every response carries scores; route low-confidence results to human review instead of trusting them blindly |

## Combining APIs into pipelines

Real solutions chain APIs, usually orchestrated by Cloud Run functions, Workflows or Dataflow:

- **Call analytics**: Speech-to-Text → Natural Language (sentiment, entities) → BigQuery. Contact-centre
  packaged version: Conversational Insights (Contact Center AI Insights).
- **Document intake**: Cloud Storage upload → Document AI classifier/splitter → specialised extractor →
  validation → BigQuery / downstream system.
- **Content moderation**: upload → Vision SafeSearch (images) / Video Intelligence explicit content
  (video) → block or send to review.
- **Multilingual analysis**: Translation → Natural Language, or let Gemini handle multilingual input
  directly.

## ⚖️ API vs custom model

| Requirement | Pick |
|---|---|
| Extract text from photos / signs | Vision API `TEXT_DETECTION` |
| Extract fields from invoices / forms | Document AI (Form Parser or specialised processor) |
| Detect *your own* product defects | AutoML image / custom model |
| Sentiment of reviews, generic | Natural Language API |
| Classify support tickets into *your* categories | Gemini prompt (few-shot) or tuned Gemini |
| Translate with fixed terminology | Translation Advanced + glossary |
| Transcribe calls with domain jargon | Speech-to-Text with model adaptation |
| E-commerce recommendations | Retail API recommendations |
| Recommendations from in-warehouse interaction data | BigQuery ML matrix factorization |
| Contact-centre virtual agent | Dialogflow CX / Agent Builder |

## ⚖️ Vision API vs Document AI vs Gemini for documents

| | Vision API OCR | Document AI | Gemini (multimodal) |
|---|---|---|---|
| Output | Raw text + positions | Structured entities, tables, key-value pairs | Free-form / JSON answer to a prompt |
| Best for | Text in images | High-volume document processing with a fixed schema | Ad-hoc questions, summarisation, flexible extraction |
| Custom schema | No | Yes (custom extractor, up-training) | Via prompt / tuning |

## 🧪 Worked scenarios

### 1. User-uploaded images
A social app must block adult or violent images at upload time, starting next week.

**Answer:** Vision API **SafeSearch detection** called from the upload backend; reject or queue for review
based on likelihood levels. No training needed.

### 2. Sentiment of support calls
A company records 10 000 support calls a day and wants a dashboard of customer sentiment per product.

**Answer:** **Speech-to-Text** (batch, with model adaptation for product names) → **Natural Language
API** sentiment/entity sentiment → BigQuery → dashboard. (Or Conversational Insights as a packaged
contact-centre solution.)

### 3. Mixed mortgage packet
Applicants upload one 80-page PDF containing pay slips, IDs and bank statements; the bank needs fields
from each document type.

**Answer:** **Document AI custom splitter/classifier** to split and label the documents, then the
matching **specialised processors** (or custom extractors) per type. Vision OCR alone gives only text.

### 4. Product catalogue in 12 languages
Brand and product names must never be translated.

**Answer:** **Translation API Advanced** with a **glossary** (batch translation for the catalogue).

### 5. Our own damage categories
An insurer wants to classify car photos into its 15 internal damage categories.

**Answer:** Not Vision label detection — use **AutoML image classification** (or a custom / tuned
multimodal model). Business-specific labels need training on your data.

## 🪤 Exam traps

- **Training a model for a generic task.** If the Vision API already detects the thing (text, landmarks,
  logos, explicit content), training AutoML is over-engineering.
- **Using an API for business-specific labels.** "Classify images into our 25 part types" → AutoML or a
  custom model, not label detection.
- **Face detection ≠ face recognition.** The Vision API does not identify people.
- **Plain OCR for forms.** Use Document AI when the requirement is fields/tables, not text.
- **Retired AutoML products** (Natural Language, Video) may appear in older questions — pick them only if
  that's what the question offers; today's equivalent is Gemini.
- **Synchronous calls for large files** — multi-page PDFs and long audio need async/batch operations
  via Cloud Storage.
- **API keys in a mobile app** — call the API from a backend with a service account.

## ✅ Key takeaways

- Generic task + no ML team + fast delivery → pre-trained API.
- Documents → Document AI; images/text/audio generic → Vision / Natural Language / Speech / Translation.
- Your own labels → AutoML, custom training, or a tuned foundation model.
- Retail recommendations need catalog + user events; quality of events matters most.
