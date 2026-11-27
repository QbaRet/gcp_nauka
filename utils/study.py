"""Study helpers shared by Quiz, Learn and Exam pages.

- Spaced repetition (simplified SM-2) and full answer history  -> ``data/study.json``
- Bookmarks and personal notes                                  -> ``data/notes.json``
- Exam simulation results                                       -> ``data/exam_history.json``
- Answer-option shuffling and common question rendering

``data/progress.json`` keeps its original meaning (last saved result per question) so the dashboard
and export page keep working unchanged.
"""

import json
import random
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from models.questions import Question
from utils import DATA_DIR
from utils.session import cache

STUDY_FILE = DATA_DIR / "study.json"
NOTES_FILE = DATA_DIR / "notes.json"
EXAM_HISTORY_FILE = DATA_DIR / "exam_history.json"

MASTERED_DAYS = 7  # a card counts as mastered once its next review is at least this far away
MAX_EASE, MIN_EASE, START_EASE = 3.0, 1.3, 2.5


# --------------------------------------------------------------------------- json storage


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    DATA_DIR.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------- spaced repetition


def question_key(qid: int) -> str:
    return str(qid)


def product_key(name: str) -> str:
    return f"p:{name}"


def load_study() -> dict[str, dict]:
    return load_json(STUDY_FILE, {})


def _schedule(rec: dict, ok: bool, today: date):
    last = rec.get("last_review")
    if ok:
        if last == today.isoformat() and rec.get("reps", 0) > 0:
            return  # already advanced today; repeating a card the same day doesn't count twice
        rec["reps"] = rec.get("reps", 0) + 1
        interval = rec.get("interval", 0)
        rec["interval"] = 1 if rec["reps"] == 1 else 3 if rec["reps"] == 2 else round(interval * rec["ease"])
        rec["ease"] = min(MAX_EASE, rec["ease"] + 0.05)
    else:
        rec["reps"] = 0
        rec["interval"] = 1
        rec["ease"] = max(MIN_EASE, rec["ease"] - 0.2)
    rec["due"] = (today + timedelta(days=rec["interval"])).isoformat()
    rec["last_review"] = today.isoformat()


def record_answers(results: dict[str, bool], source: str):
    """Log answers (card key -> correct?) to history and update their review schedule."""
    if not results:
        return
    study = load_study()
    now = datetime.now()
    for key, ok in results.items():
        rec = study.setdefault(key, {"reps": 0, "interval": 0, "ease": START_EASE, "history": []})
        rec["history"].append({"t": now.isoformat(timespec="seconds"), "ok": bool(ok), "src": source})
        _schedule(rec, bool(ok), now.date())
    save_json(STUDY_FILE, study)


def record_answer(key: str, ok: bool, source: str):
    record_answers({key: ok}, source)


def is_due(rec: dict | None, today: date | None = None) -> bool:
    return bool(rec and rec.get("due") and rec["due"] <= (today or date.today()).isoformat())


def is_mastered(rec: dict | None) -> bool:
    return bool(rec and rec.get("interval", 0) >= MASTERED_DAYS)


def due_question_ids(progress: dict[int, bool], study: dict | None = None) -> set[int]:
    """Questions to review today: scheduled reviews that are due, plus old wrong answers never scheduled."""
    study = load_study() if study is None else study
    due = {int(k) for k, rec in study.items() if not k.startswith("p:") and is_due(rec)}
    due |= {qid for qid, ok in progress.items() if not ok and question_key(qid) not in study}
    return due


def history_line(rec: dict | None, limit: int = 15) -> str:
    if not rec or not rec.get("history"):
        return "No attempts recorded yet."
    hist = rec["history"]
    ok = sum(1 for h in hist if h["ok"])
    marks = "".join("✅" if h["ok"] else "❌" for h in hist[-limit:])
    more = "… " if len(hist) > limit else ""
    nxt = f" · next review {rec['due']}" if rec.get("due") else ""
    return f"{more}{marks}  —  {ok}/{len(hist)} correct{nxt}"


# --------------------------------------------------------------------------- bookmarks & notes


def load_notes() -> dict[str, dict]:
    return load_json(NOTES_FILE, {})


def starred_ids() -> set[int]:
    return {int(k) for k, v in load_notes().items() if v.get("star")}


def _update_note(qid: int, **fields):
    notes = load_notes()
    entry = notes.setdefault(str(qid), {})
    entry.update(fields)
    if not entry.get("star") and not entry.get("note"):
        notes.pop(str(qid))
    save_json(NOTES_FILE, notes)


def _toggle_star(qid: int):
    _update_note(qid, star=not load_notes().get(str(qid), {}).get("star", False))


def _save_note_from_widget(qid: int, widget_key: str):
    _update_note(qid, note=st.session_state.get(widget_key, "").strip())


def question_tools(q: Question, ctx: str, shortcuts: bool = True):
    """Bookmark toggle plus an expander with a personal note and the answer history."""
    entry = load_notes().get(str(q.id), {})
    starred = entry.get("star", False)
    st.button(
        "⭐ Bookmarked" if starred else "☆ Bookmark",
        key=f"star_{ctx}_{q.id}",
        on_click=_toggle_star,
        args=(q.id,),
        type="tertiary",
        help="Bookmarked questions can be studied as a separate set.",
        shortcut="B" if shortcuts else None,
    )
    note_key = f"note_{ctx}_{q.id}"
    if note_key not in st.session_state:
        st.session_state[note_key] = entry.get("note", "")
    label = "📝 Note & history" + (" · has note" if entry.get("note") else "")
    with st.expander(label):
        st.text_area(
            "Your note (saved automatically)",
            key=note_key,
            on_change=_save_note_from_widget,
            args=(q.id, note_key),
            placeholder="e.g. remember: drift ≠ skew",
        )
        st.caption("History: " + history_line(load_study().get(question_key(q.id))))


# --------------------------------------------------------------------------- answer shuffling

_LETTER_PREFIX = re.compile(r"^\s*[A-Z][.)]\s+")
_ORDER_DEPENDENT = re.compile(r"\b(all|none) of the above\b|\b[A-F] (and|or|&) [A-F]\b", re.IGNORECASE)


def strip_letter(option: str) -> str:
    return _LETTER_PREFIX.sub("", option, count=1)


def _setting_changed():
    cache.set("shuffle_options", st.session_state.shuffle_options_toggle)


def shuffle_setting() -> bool:
    """Sidebar toggle (persisted) for shuffling answer options."""
    return st.sidebar.toggle(
        "🔀 Shuffle answer options",
        value=cache.get("shuffle_options", True),
        key="shuffle_options_toggle",
        on_change=_setting_changed,
        help="Stops you from memorising 'the answer is D'. Explanations still use the original letters.",
    )


def option_order(q: Question, seed, shuffle: bool) -> list[int]:
    """Original option indexes in display order (stable for a given seed)."""
    order = list(range(len(q.options)))
    if shuffle and not any(_ORDER_DEPENDENT.search(strip_letter(o)) for o in q.options):
        random.Random(f"{seed}-{q.id}").shuffle(order)
    return order


_FIRST_STEP = re.compile(r"^1[.)]\s")
_NEXT_STEP = re.compile(r"(?<=[.;:])\s+(?=[2-9][.)]\s)")  # " 2. " right after the end of the previous step
_STEP_INDENT = "\u2003\u2003"  # aligns "2. ..." under "1. ..." after the "A." prefix


def tidy_option(text: str) -> str:
    """One line per step: "1. ...\n\n2. ..." becomes markdown hard breaks, continuation lines indented."""
    text = text.strip()
    if _FIRST_STEP.match(text):  # "1. Do X. 2. Do Y." on one line -> one step per line
        text = _NEXT_STEP.sub("\n", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "  \n".join([lines[0], *(_STEP_INDENT + line for line in lines[1:])]) if lines else ""


def option_labels(q: Question, order: list[int]) -> dict[int, str]:
    """Original index -> label shown to the user (relettered when the order changed)."""
    shuffled = order != sorted(order)
    return {
        orig: f"{chr(65 + (pos if shuffled else orig))}. {tidy_option(strip_letter(q.options[orig]))}"
        if shuffled or _LETTER_PREFIX.match(q.options[orig])
        else tidy_option(q.options[orig])
        for pos, orig in enumerate(order)
    }


def correct_set(q: Question) -> set[int]:
    return set(q.answer) if isinstance(q.answer, list) else {q.answer}


# --------------------------------------------------------------------------- rendering


def render_question(q: Question):
    question = q.question if "<p>" in q.question.lower() else f"<p>{q.question}</p>"
    st.markdown(question, unsafe_allow_html=True)


def answer_input(q: Question, order: list[int], key: str, disabled: bool = False, default=None) -> set[int]:
    """Radio (single choice) or checkboxes (multiple choice). Returns chosen original indexes."""
    labels = option_labels(q, order)
    default = set(default or [])
    # the "answeropts" key gives the container a CSS class (see style.css) that draws each option as a card
    with st.container(key=f"answeropts_{key}"):
        if q.mode == "single_choice":
            idx = next((pos for pos, o in enumerate(order) if o in default), None)
            choice = st.radio("Choose an answer:", order, index=idx, format_func=labels.get, key=key, disabled=disabled)
            return {choice} if choice is not None else set()
        st.markdown(f"Choose **{len(correct_set(q))}** answers:")
        return {o for o in order if st.checkbox(labels[o], value=o in default, key=f"{key}_{o}", disabled=disabled)}


def _styled(label: str, fmt: str) -> str:
    """Apply an inline markdown format to every line of a (possibly multi-line) label."""
    lines = label.split("  \n")
    # keep the step indent outside the markers: "** text**" (space after **) is not valid markdown
    return "  \n".join(
        line[: len(line) - len(line.lstrip(_STEP_INDENT))] + fmt.format(line.lstrip(_STEP_INDENT)) for line in lines
    )


def render_answer(q: Question, order: list[int], chosen: set[int] | None = None, explanation: bool = True):
    """Show all options with the correct ones (and the user's wrong picks) highlighted."""
    labels = option_labels(q, order)
    correct = correct_set(q)
    for o in order:
        with st.container(border=True):
            if o in correct:
                st.markdown("✔ " + _styled(labels[o], ":green[**{}**]"))
            elif chosen and o in chosen:
                st.markdown("✘ " + _styled(labels[o], ":red[~~{}~~]"))
            else:
                st.markdown(_styled(labels[o], ":gray[{}]"))
    if order != sorted(order):
        mapping = ", ".join(f"{chr(65 + o)}→{chr(65 + pos)}" for pos, o in sorted(enumerate(order), key=lambda x: x[1]))
        st.caption(f"Options were shuffled. Letters in the explanation use the original order: {mapping}")
    if explanation and q.explanation:
        with st.expander("Explanation", expanded=True):
            st.markdown(q.explanation, unsafe_allow_html=True)
