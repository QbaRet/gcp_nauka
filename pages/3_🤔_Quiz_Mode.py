import logging
import random
from pathlib import Path

import streamlit as st

from utils import (
    compute_stats,
    load_progress,
    load_quizzes,
    save_progress,
    section_filter,
    set_css_style,
)
from utils.session import cache_session, clear_session_cache, load_session
from utils.study import (
    answer_input,
    correct_set,
    due_question_ids,
    option_order,
    question_key,
    question_tools,
    record_answer,
    render_answer,
    render_question,
    shuffle_setting,
    starred_ids,
)

load_session()

logger = logging.getLogger(__name__)

set_css_style(Path("style.css"))

DASHBOARD_PAGE = "🏠_Dashboard.py"


def save_progress_click(progress):
    saved = load_progress()
    saved.update(progress)
    save_progress(saved)
    clear_round_data()
    st.session_state.message = "Round results merged into overall progress."


def clear_round_data():
    st.session_state.quiz_in_progress = None
    st.session_state.quizzes = []
    st.session_state.quiz_mode_pos = 0
    st.session_state.quiz_mode_round_progress = {}
    clear_session_cache()


def start_new_round(quizzes):
    random.shuffle(quizzes)
    st.session_state.quiz_in_progress = True
    st.session_state.quizzes = quizzes
    st.session_state.quiz_mode_pos = 0
    st.session_state.quiz_mode_round_progress = {}
    st.session_state.quiz_mode_answered = False
    st.session_state.quiz_round_seed = random.randrange(1_000_000)
    cache_session()
    st.rerun()


def round_buttons():
    progress = {st.session_state.quizzes[p].id: res for p, res in st.session_state.quiz_mode_round_progress.items()}
    if st.button("Save round results to overall progress", icon="💾", on_click=save_progress_click, args=(progress,)):
        st.switch_page(DASHBOARD_PAGE)
    if st.button("Clear round data", icon="🗑️", on_click=clear_round_data):
        st.switch_page(DASHBOARD_PAGE)


def show_quiz(shuffle: bool):
    pos = st.session_state.quiz_mode_pos
    if pos >= len(st.session_state.quizzes):
        st.success("Round complete — no more questions in this shuffled round.")
        asked, correct, wrong, pct = compute_stats(st.session_state.quiz_mode_round_progress)
        st.markdown(f"Asked: {asked} — Correct: {correct} — Wrong: {wrong} — Success: {pct:.1f}%")
        round_buttons()
        return

    # show current question
    quizzes = st.session_state.quizzes
    q = quizzes[pos]
    st.header(f"Question (#{q.id}) {pos + 1} / {len(st.session_state.quizzes)}")
    st.progress(pos / len(quizzes))

    render_question(q)

    answered = st.session_state.quiz_mode_answered
    order = option_order(q, st.session_state.quiz_round_seed, shuffle)
    chosen = answer_input(q, order, key=f"choice_{pos}", disabled=answered)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    if col1.button("✅ Submit", key=f"submit_{pos}", type="primary", disabled=answered, shortcut="Enter"):
        if not chosen:
            st.warning("Please select at least one answer before submitting.")
        else:
            ok = chosen == correct_set(q)
            st.session_state.quiz_mode_round_progress[pos] = ok
            st.session_state[f"chosen_{pos}"] = chosen
            record_answer(question_key(q.id), ok, "quiz")
            st.session_state.quiz_mode_answered = True
            cache_session()
            st.rerun()

    caption = "➡️ Next Question" if answered else "⏭️ Skip Question"
    if col2.button(caption, key=f"next_{pos}", shortcut="Right"):
        st.session_state.quiz_mode_pos += 1
        st.session_state.quiz_mode_answered = False
        cache_session()
        st.rerun()

    if answered:
        if st.session_state.quiz_mode_round_progress[pos]:
            st.success("Correct ✅")
        else:
            st.error("Incorrect ❌")
        st.markdown("### Correct Answer:")
        render_answer(q, order, chosen=st.session_state.get(f"chosen_{pos}"))

    question_tools(q, ctx="quiz")

    st.markdown("---")
    # small live round stats
    asked, correct, wrong, pct = compute_stats(st.session_state.quiz_mode_round_progress)
    st.markdown(f"Round progress — asked: {asked}, correct: {correct}, wrong: {wrong}, success: {pct:.1f}%")
    st.caption("Shortcuts: Enter = submit · → = next · B = bookmark")

    col1, col2 = st.columns(2)
    with col1:
        with st.popover("🔄 Restart Round"):
            st.warning("Restarting will lose current round progress. Are you sure?")
            if st.button("Yes, restart", type="primary"):
                clear_round_data()
                st.session_state.message = "Starting new round..."
                start_new_round(quizzes)
    with col2:
        with st.popover("🚫 Stop Round"):
            asked, correct, wrong, pct = compute_stats(st.session_state.quiz_mode_round_progress)
            st.info(f"Round stats — asked: {asked}, correct: {correct}, wrong: {wrong}, success: {pct:.1f}%")
            round_buttons()


def show_stats():
    progress = load_progress()
    answered_incorrectly, not_answered, answered_correctly = load_quizzes(progress)

    if not answered_incorrectly and not not_answered and not answered_correctly:
        st.warning("No quizzes found in data/quizzes.jsonl")
        return

    matches = section_filter(answered_incorrectly + not_answered + answered_correctly)
    answered_incorrectly = [q for q in answered_incorrectly if matches(q)]
    not_answered = [q for q in not_answered if matches(q)]
    answered_correctly = [q for q in answered_correctly if matches(q)]

    container = st.container()
    with container:
        cols = st.columns(3)
        with cols[0]:
            st.metric("Answered correctly", len(answered_correctly))
        with cols[1]:
            st.metric("Answered incorrectly", len(answered_incorrectly))
        with cols[2]:
            st.metric("Not answered", len(not_answered))

    special = st.radio(
        "Question set",
        ["Standard", "📅 Due for review", "⭐ Bookmarked"],
        horizontal=True,
        key="quiz_special_set",
        help="Standard = not answered (+ wrong ones when included below). "
        "Due for review = spaced-repetition reviews scheduled for today or earlier.",
    )

    if st.button("Start Round", type="primary"):
        everything = answered_incorrectly + not_answered + answered_correctly
        if special == "📅 Due for review":
            due = due_question_ids(progress)
            quizzes = [q for q in everything if q.id in due]
        elif special == "⭐ Bookmarked":
            stars = starred_ids()
            quizzes = [q for q in everything if q.id in stars]
        elif st.session_state.wrong_answered_inclusion:
            pct = st.session_state.correct_answered_percentage
            num_to_include = int(len(answered_correctly) * pct / 100)
            quizzes = not_answered + answered_incorrectly
            if num_to_include > 0:
                logger.info(f"Including {num_to_include} previously correct answered questions in the round.")
                quizzes += random.sample(answered_correctly, num_to_include)
        else:
            quizzes = not_answered

        if not quizzes:
            st.warning("No quizzes left to answer for this round.")
        else:
            st.session_state.message = "Starting new round..."
            start_new_round(quizzes)

    st.info("Press 'Start Round' to begin the quiz.")

    if special == "Standard":
        if st.toggle("➕ Include Wrong Answered", value=False, key="wrong_answered_inclusion"):
            st.info("Previous wrong answers will be included in the quiz.")

            st.number_input(
                "Percentage of correct answered to include",
                min_value=0,
                max_value=100,
                value=0,
                step=10,
                key="correct_answered_percentage",
            )


def main():
    st.set_page_config(page_title="Quiz Mode")

    st.title("Quiz Mode")
    shuffle = shuffle_setting()

    if st.session_state.quiz_in_progress and st.session_state.quizzes:
        show_quiz(shuffle)
    else:
        st.session_state.quiz_in_progress = None
        show_stats()


if __name__ == "__main__":
    main()
