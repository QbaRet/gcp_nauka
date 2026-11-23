"""Theory: topic lessons for the PMLE exam, cheat sheets, search, reading progress and practice links."""

import re
from pathlib import Path

import streamlit as st

from utils import load_progress, load_quizzes, set_css_style
from utils.sections import THEORY_LESSON, set_section_preset
from utils.study import due_question_ids
from utils.theory import (
    CHEAT_SHEET_MARK,
    Lesson,
    load_lessons,
    load_theory_progress,
    matches_lesson,
    read_count,
    set_note,
    set_read,
    split_sections,
)

LEARN_PAGE = "pages/6_🎓_Learn_Mode.py"
QUIZ_PAGE = "pages/3_🤔_Quiz_Mode.py"
EXAM_PAGE = "pages/7_⏱️_Exam_Simulation.py"

st.set_page_config(page_title="Theory", layout="wide")
set_css_style(Path("style.css"))

ABOUT = """
**How to use these lessons.** Read a lesson, then press **Practice** at the bottom to answer the questions
from the bank linked to that topic. Each lesson has decision tables (⚖️, also collected on the *Cheat
sheets* tab), worked exam-style scenarios with hidden answers (🧪), the typical exam traps (🪤) and key
takeaways (✅).

**Naming.** The question bank uses the current product names; the lessons and exam guide 3.1 still use
the older ones. Old → new:

| Older name (lessons, exam guide 3.1) | Current name (questions, docs) |
|---|---|
| Vertex AI | **Gemini Enterprise Agent Platform** (short: *Agent Platform*) |
| Vertex AI Pipelines / Workbench / Feature Store / Experiments / … | Agent Platform Pipelines / Workbench / Feature Store / Experiments / … |
| Vertex ML Metadata, Vertex AI SDK | Agent Platform ML Metadata, Agent Platform SDK |
| Matching Engine | Vector Search |
| Dataproc (Serverless) | Managed Service for Apache Spark (serverless) |
| Cloud Composer | Managed Service for Apache Airflow |
| Cloud Functions | Cloud Run functions |
| Cloud DLP / Data Loss Prevention API | Sensitive Data Protection (DLP API) |
| Data Catalog → Dataplex Universal Catalog | Knowledge Catalog |
| Data Studio | Looker Studio |
| Operations suite (Stackdriver) | Google Cloud Observability |
| Cloud Datastore | Firestore in Datastore mode |

Unchanged on purpose: *Vertex Explainable AI* (deprecated under that name), *Vertex AI Search* and *Vertex
AI Agent Builder* (renamed several times since — no confirmed current name), AutoML, Model Garden.

**Exam guide versions.** Domain weights in guide 3.1 → newer guide (2026):

| Domain | 3.1 | 2026 |
|---|---|---|
| 1. Architecting low-code AI solutions | 13 % | ~13 % |
| 2. Collaborating to manage data and models | ~14 % | ~16 % |
| 3. Scaling prototypes into ML models | ~18 % | ~21 % |
| 4. Serving and scaling models | ~20 % | ~20 % |
| 5. Automating and orchestrating ML pipelines | ~22 % | ~18 % |
| 6. Monitoring AI solutions | ~13 % | ~13 % |

The newer guide adds more generative AI (Model Garden, tuning Gemini, LLM-as-a-judge), Model Armor,
Ray on Vertex AI and Managed Airflow. Facts in the lessons were checked against the linked Google Cloud
documentation on **22 Nov 2026**; Google Cloud changes often, so follow the sources when in doubt.
"""


# --------------------------------------------------------------------------- state helpers


def selected_lesson(lessons: list[Lesson]) -> Lesson:
    ids = [lesson.id for lesson in lessons]
    preset = st.session_state.pop("theory_lesson_preset", None)
    if preset in ids:
        st.session_state.theory_lesson = preset
    if st.session_state.get("theory_lesson") not in ids:
        from_url = st.query_params.get("lesson")
        if from_url in ids:
            st.session_state.theory_lesson = from_url
        else:  # first unread lesson
            progress = load_theory_progress()
            st.session_state.theory_lesson = next((i for i in ids if not progress.get(i, {}).get("read")), ids[0])
    return lessons[ids.index(st.session_state.theory_lesson)]


def select(lesson_id: str):
    st.session_state.theory_lesson = lesson_id
    st.query_params["lesson"] = lesson_id


def _read_changed(lesson_id: str):
    set_read(lesson_id, st.session_state[f"theory_read_{lesson_id}"])


def _note_changed(lesson_id: str):
    set_note(lesson_id, st.session_state.get(f"theory_note_{lesson_id}", ""))


def practice(target: str, lesson: Lesson):
    sections = [lesson.title]
    if target in ("learn", "flashcards"):
        set_section_preset("learn_section", THEORY_LESSON, sections)
        st.session_state.learn_preset = {
            "mode": "🧠 Learn" if target == "learn" else "🃏 Flashcards",
            "sources": ["Wrong answered", "Not answered", "📅 Due for review"],
        }
        st.switch_page(LEARN_PAGE)
    elif target == "quiz":
        set_section_preset("section_filter", THEORY_LESSON, sections)
        st.switch_page(QUIZ_PAGE)
    else:
        set_section_preset("exam_section", THEORY_LESSON, sections)
        st.session_state.exam_n = 10
        st.switch_page(EXAM_PAGE)


# --------------------------------------------------------------------------- rendering


SCENARIO_MARK = "🧪"


def render_scenarios(body: str):
    """``### title`` blocks; text after ``**Answer:**`` is hidden in an expander."""
    for block in re.split(r"^### +", body, flags=re.MULTILINE):
        if not block.strip():
            continue
        title, _, text = block.partition("\n")
        question, _, answer = text.partition("**Answer:**")
        with st.container(border=True):
            st.markdown(f"**{title.strip()}**\n\n{question.strip()}")
            if answer.strip():
                with st.expander("Show answer"):
                    st.markdown(answer.strip())


def render_body(lesson: Lesson):
    for heading, body in split_sections(lesson.body()):
        if not heading:
            st.markdown(body)
        elif heading.startswith(CHEAT_SHEET_MARK):
            with st.container(border=True):
                st.markdown(f"### {heading}")
                st.markdown(body)
        elif heading.startswith("✅"):
            st.markdown(f"## {heading}")
            st.success(body)
        elif heading.startswith("🪤"):
            st.markdown(f"## {heading}")
            st.warning(body)
        elif heading.startswith(SCENARIO_MARK):
            st.markdown(f"## {heading}")
            st.caption("Try to answer each scenario yourself before revealing the answer.")
            render_scenarios(body)
        else:
            st.markdown(f"## {heading}\n\n{body}")


def practice_stats(lesson: Lesson) -> dict:
    progress = load_progress()
    due = due_question_ids(progress)
    related = [q for g in load_quizzes(progress) for q in g if matches_lesson(lesson, q)]
    seen = [q for q in related if q.id in progress]
    correct = sum(1 for q in seen if progress[q.id])
    return {
        "total": len(related),
        "seen": len(seen),
        "accuracy": correct / len(seen) * 100 if seen else None,
        "readiness": correct / len(related) * 100 if related else 0,
        "due": sum(1 for q in related if q.id in due),
    }


def show_lesson(lesson: Lesson, lessons: list[Lesson]):
    idx = lessons.index(lesson)
    st.title(f"{idx + 1}. {lesson.title}")
    st.caption(" · ".join(lesson.domains) + f" · ~{lesson.minutes} min read")
    st.markdown(f"*{lesson.summary}*")

    stats = practice_stats(lesson)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Linked questions", stats["total"])
    c2.metric("Answered", f"{stats['seen']} / {stats['total']}")
    c3.metric("Accuracy", f"{stats['accuracy']:.0f}%" if stats["accuracy"] is not None else "—")
    c4.metric("📅 Due", stats["due"])
    st.divider()

    render_body(lesson)

    st.markdown("#### 📎 Sources")
    st.markdown("\n".join(f"- [{title}]({url})" for title, url in lesson.sources))

    st.divider()
    entry = load_theory_progress().get(lesson.id, {})
    read_key, note_key = f"theory_read_{lesson.id}", f"theory_note_{lesson.id}"
    if note_key not in st.session_state:
        st.session_state[note_key] = entry.get("note", "")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.toggle(
            "✅ I've read this lesson",
            value=bool(entry.get("read")),
            key=read_key,
            on_change=_read_changed,
            args=(lesson.id,),
        )
        if entry.get("read"):
            st.caption(f"Marked as read on {entry['read']}")
    c2.text_area(
        "📝 Your notes for this lesson (saved automatically)",
        key=note_key,
        on_change=_note_changed,
        args=(lesson.id,),
        height=110,
    )

    with st.container(border=True):
        st.markdown(f"### 🎯 Practice this topic — {stats['total']} linked questions")
        st.progress(stats["readiness"] / 100, text=f"Readiness {stats['readiness']:.0f}% (correct ÷ all linked)")
        b1, b2, b3, b4 = st.columns(4)
        disabled = stats["total"] == 0
        if b1.button("🧠 Learn", type="primary", width="stretch", disabled=disabled):
            practice("learn", lesson)
        if b2.button("🃏 Flashcards", width="stretch", disabled=disabled):
            practice("flashcards", lesson)
        if b3.button("🤔 Quiz round", width="stretch", disabled=disabled):
            practice("quiz", lesson)
        if b4.button("⏱️ Mini exam (10)", width="stretch", disabled=disabled):
            practice("exam", lesson)

    c1, _, c3 = st.columns([1, 2, 1])
    if idx > 0:
        c1.button(f"⬅️ {lessons[idx - 1].title}", on_click=select, args=(lessons[idx - 1].id,), width="stretch")
    if idx < len(lessons) - 1:
        c3.button(
            f"{lessons[idx + 1].title} ➡️",
            on_click=select,
            args=(lessons[idx + 1].id,),
            type="primary",
            width="stretch",
        )


def show_navigation(lessons: list[Lesson], current: Lesson):
    done, total = read_count()
    st.progress(done / total if total else 0, text=f"Read {done} / {total} lessons")
    progress = load_theory_progress()
    domain = None
    for i, lesson in enumerate(lessons):
        first = lesson.domains[0] if lesson.domains else ""
        if first != domain:
            domain = first
            st.caption(domain)
        mark = "✅" if progress.get(lesson.id, {}).get("read") else "▫️"
        st.button(
            f"{mark} {i + 1}. {lesson.title}",
            key=f"nav_{lesson.id}",
            on_click=select,
            args=(lesson.id,),
            type="primary" if lesson.id == current.id else "tertiary",
            width="stretch",
        )


def show_cheat_sheets(lessons: list[Lesson]):
    st.caption("All decision tables from the lessons in one place — good for a last review before the exam.")
    titles = ["All lessons"] + [lesson.title for lesson in lessons]
    pick = st.selectbox("Lesson", titles, key="cheat_lesson")
    for lesson in lessons:
        if pick != "All lessons" and lesson.title != pick:
            continue
        sheets = [(h, b) for h, b in split_sections(lesson.body()) if h.startswith(CHEAT_SHEET_MARK)]
        if not sheets:
            continue
        st.markdown(f"## {lesson.title}")
        for heading, body in sheets:
            with st.container(border=True):
                st.markdown(f"### {heading}")
                st.markdown(body)


def show_search(lessons: list[Lesson]):
    query = st.text_input("Search the lessons", placeholder="e.g. Reduction Server, skew, TRANSFORM", key="theory_q")
    if len(query.strip()) < 2:
        st.caption("Type at least two characters.")
        return
    pattern = re.compile(re.escape(query.strip()), re.IGNORECASE)
    hits = 0
    for lesson in lessons:
        for heading, body in split_sections(lesson.body()):
            if not (pattern.search(body) or pattern.search(heading)):
                continue
            hits += 1
            m = pattern.search(body)
            snippet = ""
            if m:
                start = max(0, m.start() - 80)
                snippet = ("…" if start else "") + body[start : m.end() + 120].replace("\n", " ") + "…"
            with st.expander(f"{lesson.title} › {heading or 'Introduction'}"):
                if snippet:
                    st.caption(snippet)
                st.markdown(body)
                st.button("Open lesson", key=f"open_{lesson.id}_{hits}", on_click=select, args=(lesson.id,))
    if not hits:
        st.info("No matches.")
    else:
        st.caption(f"{hits} matching section(s). “Open lesson” selects it on the Lessons tab.")


def main():
    lessons = load_lessons()
    if not lessons:
        st.error("No lessons found in theory/lessons.json")
        return
    current = selected_lesson(lessons)

    with st.expander("ℹ️ About these lessons — naming, exam guide versions, sources"):
        st.markdown(ABOUT)

    tab_lessons, tab_cheats, tab_search = st.tabs(["📚 Lessons", "⚖️ Cheat sheets", "🔎 Search"])
    with tab_lessons:
        nav, main_col = st.columns([1, 3], gap="large")
        with nav:
            show_navigation(lessons, current)
        with main_col:
            show_lesson(current, lessons)
    with tab_cheats:
        show_cheat_sheets(lessons)
    with tab_search:
        show_search(lessons)


main()
