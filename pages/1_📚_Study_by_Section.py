"""Study by section: per-section stats and one-click study of the chosen sections."""

from pathlib import Path

import pandas as pd
import streamlit as st

from utils import load_progress, load_quizzes, set_css_style
from utils.sections import (
    EXAM_DOMAIN,
    FILTER_FIELDS,
    THEORY_LESSON,
    question_sections,
    set_section_preset,
)
from utils.study import (
    due_question_ids,
    is_mastered,
    load_study,
    question_key,
    starred_ids,
)

LEARN_PAGE = "pages/6_🎓_Learn_Mode.py"
QUIZ_PAGE = "pages/3_🤔_Quiz_Mode.py"
EXAM_PAGE = "pages/7_⏱️_Exam_Simulation.py"

SORTS = {
    "Weakest first": (["score", "questions"], [True, False]),
    "Most due for review": (["due", "questions"], [False, False]),
    "Least covered first": (["seen_pct", "questions"], [True, False]),
    "Most questions": (["questions"], [False]),
    "A → Z": (["section"], [True]),
}

st.set_page_config(page_title="Study by Section", layout="wide")
set_css_style(Path("style.css"))


def section_table(section_type: str) -> pd.DataFrame:
    progress = load_progress()
    study = load_study()
    due = due_question_ids(progress, study)
    stars = starred_ids()

    stats: dict[str, dict] = {}
    for group in load_quizzes(progress):
        for q in group:
            rec = study.get(question_key(q.id))
            for section in question_sections(q, section_type):
                s = stats.setdefault(
                    section, {"questions": 0, "seen": 0, "correct": 0, "due": 0, "mastered": 0, "starred": 0}
                )
                s["questions"] += 1
                if q.id in progress:
                    s["seen"] += 1
                    s["correct"] += bool(progress[q.id])
                s["due"] += q.id in due
                s["mastered"] += is_mastered(rec)
                s["starred"] += q.id in stars

    df = pd.DataFrame([{"section": k, **v} for k, v in stats.items()])
    if df.empty:
        return df
    df["seen_pct"] = df["seen"] / df["questions"] * 100
    df["accuracy"] = (df["correct"] / df["seen"].where(df["seen"] > 0) * 100).round(0)
    df["mastered_pct"] = df["mastered"] / df["questions"] * 100
    # readiness: accuracy weighted by how much of the section you've seen (unseen counts as 0)
    df["score"] = df["correct"] / df["questions"] * 100
    return df


def go_study(target: str, sections: list[str], section_type: str, sources: list[str] | None = None):
    if target in ("learn", "flashcards"):
        set_section_preset("learn_section", section_type, sections)
        st.session_state.learn_preset = {
            "mode": "🧠 Learn" if target == "learn" else "🃏 Flashcards",
            "sources": sources or ["Wrong answered", "Not answered", "📅 Due for review"],
        }
        st.switch_page(LEARN_PAGE)
    elif target == "quiz":
        set_section_preset("section_filter", section_type, sections)
        st.switch_page(QUIZ_PAGE)
    elif target == "exam":
        set_section_preset("exam_section", section_type, sections)
        st.session_state.exam_n = 20
        st.switch_page(EXAM_PAGE)


def main():
    st.title("📚 Study by Section")
    st.caption(
        "Pick one or more sections in the table, then choose how to study them. "
        "Readiness = correct answers ÷ all questions in the section (unseen questions count as not known yet)."
    )

    c1, c2, c3, c4 = st.columns([2.2, 1.4, 1.6, 1.2], vertical_alignment="bottom")
    section_type = c1.radio("Section type", list(FILTER_FIELDS), horizontal=True, key="sections_type")
    sort = c2.selectbox("Sort", list(SORTS), key="sections_sort")
    search = c3.text_input("Search", placeholder="e.g. monitoring", key="sections_search")
    is_domain = section_type in (EXAM_DOMAIN, THEORY_LESSON)
    min_q = c4.number_input("Min questions", 1, 100, 1 if is_domain else 5, key=f"sections_min_{section_type}")

    df = section_table(section_type)
    if df.empty:
        st.warning("No quizzes found in data/quizzes.jsonl")
        return
    if is_domain:
        st.caption(
            "Exam domains follow the official PMLE exam guide and are assigned from question tags (approximate)."
        )

    view = df[df["questions"] >= min_q]
    if search:
        view = view[view["section"].str.contains(search, case=False, regex=False)]
    by, asc = SORTS[sort]
    view = view.sort_values(by, ascending=asc).reset_index(drop=True)

    if view.empty:
        st.info("No sections match. Lower 'Min questions' or change the search.")
        return

    event = st.dataframe(
        view[["section", "questions", "seen_pct", "accuracy", "score", "mastered_pct", "due", "starred"]],
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="multi-row",
        key=f"sections_table_{section_type}",
        height=min(38 * (len(view) + 1) + 3, 560),
        column_config={
            "section": st.column_config.TextColumn("Section", width="large"),
            "questions": st.column_config.NumberColumn("Questions"),
            "seen_pct": st.column_config.ProgressColumn("Seen", format="%.0f%%", min_value=0, max_value=100),
            "accuracy": st.column_config.NumberColumn("Accuracy", format="%.0f%%", help="Correct ÷ answered"),
            "score": st.column_config.ProgressColumn("Readiness", format="%.0f%%", min_value=0, max_value=100),
            "mastered_pct": st.column_config.ProgressColumn(
                "Mastered", format="%.0f%%", min_value=0, max_value=100, help="Next review ≥ 7 days away"
            ),
            "due": st.column_config.NumberColumn("📅 Due", help="Questions to review today"),
            "starred": st.column_config.NumberColumn("⭐"),
        },
    )

    picked = [view.iloc[i]["section"] for i in event.selection.rows]

    with st.container(border=True):
        if picked:
            sel = view[view["section"].isin(picked)]
            st.markdown(f"**Selected:** {', '.join(picked)}")
            st.caption(
                f"{int(sel['questions'].sum())} question tags · {int(sel['due'].sum())} due for review "
                "(questions in several selected sections are counted once when studying)"
            )
        else:
            weakest = view.sort_values(["score", "questions"], ascending=[True, False])["section"].head(3).tolist()
            st.markdown("**Nothing selected** — the buttons below use your 3 weakest sections in this list:")
            st.caption(", ".join(weakest))
            picked = weakest

        b1, b2, b3, b4, b5 = st.columns(5)
        if b1.button("🧠 Learn", type="primary", width="stretch"):
            go_study("learn", picked, section_type)
        if b2.button("🃏 Flashcards", width="stretch"):
            go_study("flashcards", picked, section_type)
        if b3.button("📅 Review due", width="stretch", help="Learn mode with only the due questions"):
            go_study("learn", picked, section_type, sources=["📅 Due for review"])
        if b4.button("🤔 Quiz round", width="stretch"):
            go_study("quiz", picked, section_type)
        if b5.button("⏱️ Mini exam (20)", width="stretch"):
            go_study("exam", picked, section_type)


main()
