from pathlib import Path

import streamlit as st

from dashboard import show_dashboard
from utils import reset_progress, save_progress, set_css_style

st.set_page_config(page_title="Quiz Learner", initial_sidebar_state="collapsed", layout="wide")


def show_study_shortcuts():
    from utils import load_progress
    from utils.study import due_question_ids, starred_ids
    from utils.theory import read_count

    due = len(due_question_ids(load_progress()))
    stars = len(starred_ids())
    read, lessons = read_count()
    with st.container(border=True):
        st.markdown(
            f"### 📅 {due} question(s) due for review today · ⭐ {stars} bookmarked · 📖 {read}/{lessons} lessons read"
        )
        c0, c1, c2, c3, c4 = st.columns(5)
        if c0.button("📖 Theory", width="stretch"):
            st.switch_page("pages/0_📖_Theory.py")
        if c1.button("📅 Review due now", type="primary", disabled=due == 0, width="stretch"):
            st.session_state.learn_preset = {"mode": "🧠 Learn", "sources": ["📅 Due for review"]}
            st.switch_page("pages/6_🎓_Learn_Mode.py")
        if c2.button("📚 Study by section", width="stretch"):
            st.switch_page("pages/1_📚_Study_by_Section.py")
        if c3.button("🃏 Flashcards", width="stretch"):
            st.session_state.learn_preset = {"mode": "🃏 Flashcards", "sources": ["Wrong answered", "Not answered"]}
            st.switch_page("pages/6_🎓_Learn_Mode.py")
        if c4.button("⏱️ Exam simulation", width="stretch"):
            st.switch_page("pages/7_⏱️_Exam_Simulation.py")


def main():
    st.set_page_config(page_title="Quiz Learner", initial_sidebar_state="collapsed", layout="wide")

    set_css_style(Path("style.css"))

    st.title("Quiz Learner — Dashboard")

    stats = show_dashboard()

    show_study_shortcuts()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start", type="primary"):
            if stats["total"] == 0:
                st.warning("⚠️ No quizzes found in data/quizzes.jsonl")
                return
            # initialize a flag and navigate to the Quiz Mode page
            st.session_state.quiz_in_progress = False
            st.session_state.quizzes = None
            st.session_state.quiz_mode_pos = 0
            st.session_state.quiz_mode_round_progress = {}
            st.session_state.quiz_mode_answered = False

            st.switch_page("pages/3_🤔_Quiz_Mode.py")

    with col2:
        if st.button("‼️ Reset progress"):
            st.warning("This will clear all your progress and cannot be undone.", icon="⚠️")
            if st.button(
                "Yes",
                icon="🚨",
            ):
                reset_progress()
                progress = {}
                save_progress(progress)
                st.rerun()


if __name__ == "__main__":
    main()
