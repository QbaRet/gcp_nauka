"""Sections ("działy") used to filter and group questions.

Four section types are available:

- **Exam domain** — the six official PMLE exam guide sections. Questions don't carry this label, so it
  is derived from their tags with keyword rules (approximate, a question can land in more than one).
- **GCP topic / ML topic / GCP product** — the raw tags from ``data/quizzes.jsonl``. Tags that differ
  only in case or spacing ("Model Training" vs "model training") are merged.
"""

from collections import Counter
from functools import lru_cache

import streamlit as st

from models.questions import Question

EXAM_DOMAIN = "Exam domain"
THEORY_LESSON = "Theory lesson"
FILTER_FIELDS = {
    EXAM_DOMAIN: None,
    THEORY_LESSON: None,
    "GCP topic": "gcp_topics",
    "ML topic": "ml_topics",
    "GCP product": "gcp_products",
}
OTHER_DOMAIN = "Other / general"

# Keyword rules (matched as substrings of lower-cased tags and product names, see ``match_form``).
# Legacy and current product names are both listed (e.g. "dataproc" / "apache spark").
EXAM_DOMAINS: dict[str, list[str]] = {
    "1. Architecting low-code AI solutions": [
        "automl",
        "bigquery ml",
        "bqml",
        "pre-trained",
        "pretrained",
        "vision api",
        "natural language api",
        "translation",
        "speech",
        "document ai",
        "video intelligence",
        "model garden",
        "gemini",
        "generative",
        "llm",
        "prompt",
        "rag",
        "agent builder",
        "vertex ai search",
        "dialogflow",
        "recommendations ai",
        "low-code",
        "no-code",
        "problem framing",
        "ml solution architecture",
        "managed services",
        "cloud apis",
    ],
    "2. Collaborating to manage data and models": [
        "data storage",
        "data preprocessing",
        "data preparation",
        "data ingestion",
        "data processing",
        "data transformation",
        "data quality",
        "data labeling",
        "data cleaning",
        "data collection",
        "data splitting",
        "exploratory data analysis",
        "eda",
        "data visualization",
        "data analysis",
        "feature engineering",
        "feature store",
        "feature management",
        "feature selection",
        "one-hot",
        "categorical",
        "encoding",
        "preprocessing",
        "notebook",
        "workbench",
        "jupyter",
        "experiment",
        "dataproc",
        "apache spark",
        "data privacy",
        "data security",
        "pii",
        "dlp",
        "sensitive data",
        "compliance",
        "etl",
        "data management",
        "data leakage",
        "sampling",
        "imbalanced",
        "tabular data",
        "structured data",
    ],
    "3. Scaling prototypes into ML models": [
        "model training",
        "training",
        "hyperparameter",
        "tuning",
        "gpu",
        "tpu",
        "accelerat",
        "tensorflow",
        "keras",
        "pytorch",
        "xgboost",
        "scikit",
        "deep learning",
        "neural network",
        "transfer learning",
        "model development",
        "model building",
        "overfitting",
        "regularization",
        "convergence",
        "batch size",
        "learning rate",
        "classification",
        "regression",
        "clustering",
        "forecasting",
        "computer vision",
        "natural language processing",
        "nlp",
        "object detection",
        "recommendation",
        "model evaluation",
        "evaluation",
        "metrics",
        "precision",
        "recall",
        "accuracy",
        "auc",
        "f1",
        "loss",
        "model selection",
        "model comparison",
        "model optimization",
        "supervised",
        "embedding",
    ],
    "4. Serving and scaling models": [
        "model deployment",
        "deployment",
        "model serving",
        "serving",
        "online prediction",
        "batch prediction",
        "prediction",
        "inference",
        "endpoint",
        "latency",
        "autoscaling",
        "scalability",
        "traffic splitting",
        "a/b",
        "canary",
        "model registry",
        "model registration",
        "model versioning",
        "model export",
        "custom container",
        "containerization",
        "real-time",
        "quantization",
        "edge",
        "tflite",
        "throughput",
    ],
    "5. Automating and orchestrating ML pipelines": [
        "pipeline",
        "mlops",
        "orchestration",
        "kubeflow",
        "tfx",
        "automation",
        "ci/cd",
        "cloud build",
        "composer",
        "airflow",
        "retraining",
        "metadata",
        "lineage",
        "artifact",
        "reproducibility",
        "version control",
        "scheduling",
        "model management",
        "workflow",
    ],
    "6. Monitoring AI solutions": [
        "monitoring",
        "drift",
        "skew",
        "explainab",
        "explainable",
        "feature attribution",
        "interpretab",
        "feature importance",
        "fairness",
        "bias",
        "responsible ai",
        "logging",
        "alerting",
        "troubleshoot",
        "debugging",
        "model performance",
        "data validation",
        "model validation",
    ],
}


def _norm(tag: str) -> str:
    return " ".join(tag.lower().split())


# Current product names that would trip keyword rules written as substrings ("gemini" is gen AI, "cloud run"
# and "edge" in "knowl-edge" are serving), mapped to a neutral form used only for matching.
_MATCH_ALIASES = {
    "gemini enterprise agent platform": "agent platform",
    "cloud run function": "cloud function",
    "knowledge catalog": "data catalog",
}


def match_form(tag: str) -> str:
    """Normalised tag used for keyword matching (exam domains, theory lessons)."""
    text = _norm(tag)
    for new, neutral in _MATCH_ALIASES.items():
        text = text.replace(new, neutral)
    return text


def exam_domains(q: Question) -> list[str]:
    """Exam domains a question belongs to: every domain scoring at least half of the best one."""
    texts = [match_form(t) for t in (q.gcp_topics or []) + (q.ml_topics or []) + (q.gcp_products or [])]
    scores = {
        domain: sum(1 for t in texts if any(kw in t for kw in keywords)) for domain, keywords in EXAM_DOMAINS.items()
    }
    best = max(scores.values())
    if best == 0:
        return [OTHER_DOMAIN]
    return [d for d, s in sorted(scores.items(), key=lambda kv: -kv[1]) if s * 2 >= best]


def primary_domain(q: Question) -> str:
    return exam_domains(q)[0]


@lru_cache(maxsize=8)
def _display_names(field: str, quiz_fingerprint: tuple) -> dict[str, str]:
    """Map normalised tag -> the most common spelling of that tag."""
    from utils import load_quizzes

    variants: dict[str, Counter] = {}
    for group in load_quizzes({}):
        for q in group:
            for tag in getattr(q, field) or []:
                variants.setdefault(_norm(tag), Counter())[tag.strip()] += 1
    return {k: c.most_common(1)[0][0] for k, c in variants.items()}


def _fingerprint() -> tuple:
    from utils import QUIZ_FILE

    stat = QUIZ_FILE.stat() if QUIZ_FILE.exists() else None
    return (stat.st_mtime, stat.st_size) if stat else ()


def question_sections(q: Question, section_type: str) -> list[str]:
    """Sections of the given type a question belongs to (deduplicated, display spelling)."""
    if section_type == EXAM_DOMAIN:
        return exam_domains(q)
    if section_type == THEORY_LESSON:
        from utils.theory import question_lessons

        return question_lessons(q)
    field = FILTER_FIELDS[section_type]
    names = _display_names(field, _fingerprint())
    out = []
    for tag in getattr(q, field) or []:
        name = names.get(_norm(tag), tag.strip())
        if name not in out:
            out.append(name)
    return out


def section_counts(questions: list[Question], section_type: str) -> Counter:
    return Counter(s for q in questions for s in question_sections(q, section_type))


def set_section_preset(key_prefix: str, section_type: str, values: list[str]):
    """Pre-select sections on another page; applied the next time that page renders its filter."""
    st.session_state[f"{key_prefix}_preset"] = (section_type, list(values))


def section_filter(all_quizzes, key_prefix: str = "section_filter"):
    """Render section filter controls and return a predicate selecting matching questions."""
    field_key, values_key = f"{key_prefix}_field", f"{key_prefix}_values"
    preset = st.session_state.pop(f"{key_prefix}_preset", None)
    if preset:
        st.session_state[field_key], st.session_state[values_key] = preset

    with st.expander("🗂️ Filter by section", expanded=bool(st.session_state.get(values_key))):
        section_type = st.radio("Section type", list(FILTER_FIELDS), horizontal=True, key=field_key)
        counts = section_counts(all_quizzes, section_type)
        if section_type == EXAM_DOMAIN:
            options = sorted(counts)
        elif section_type == THEORY_LESSON:
            from utils.theory import load_lessons

            options = [lesson.title for lesson in load_lessons() if lesson.title in counts]
        else:
            options = [t for t, _ in counts.most_common()]
        # drop selections that don't exist for the newly chosen section type
        st.session_state[values_key] = [v for v in st.session_state.get(values_key, []) if v in counts]
        selected = st.multiselect(
            "Sections (empty = all questions)",
            options,
            format_func=lambda t: f"{t} ({counts[t]})",
            key=values_key,
        )
        if section_type == EXAM_DOMAIN:
            st.caption("Exam domains are assigned from question tags, so they are approximate.")

    if not selected:
        return lambda q: True
    selected_set = set(selected)
    return lambda q: bool(selected_set.intersection(question_sections(q, section_type)))
