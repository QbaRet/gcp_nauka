"""Exam simulation: a timed set of questions with no feedback until the end.

Like the real PMLE exam (50–60 questions, 2 hours): you can move back and forth, flag questions for
review, and you only see the results once you finish or the time runs out. Results are broken down by
exam domain, added to your answer history / review schedule and kept in data/exam_history.json.
"""

import random
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import (
    load_progress,
    load_quizzes,
    save_progress,
    section_filter,
    set_css_style,
)
from utils.sections import EXAM_DOMAIN, EXAM_DOMAINS, primary_domain, set_section_preset
from utils.session import cache
from utils.study import (
    EXAM_HISTORY_FILE,
    answer_input,
    correct_set,
    load_json,
    option_order,
    question_key,
    question_tools,
    record_answers,
    render_answer,
    render_question,
    save_json,
    shuffle_setting,
)

CACHE_KEY = "exam_state"
PASS_MARK = 70  # Google doesn't publish the passing score; ~70% is the commonly used target
# Approximate share of each domain in the official PMLE exam guide
DOMAIN_WEIGHTS = dict(zip(EXAM_DOMAINS, [0.13, 0.14, 0.18, 0.20, 0.22, 0.13]))

set_css_style(Path("style.css"))


# --------------------------------------------------------------------------- state


def get_state() -> dict | None:
    if "exam_state" not in st.session_state:
        st.session_state.exam_state = cache.get(CACHE_KEY)
    return st.session_state.exam_state


def save_state(state: dict | None):
    st.session_state.exam_state = state
    if state is None:
        cache.delete(CACHE_KEY)
    else:
        cache.set(CACHE_KEY, state)


def questions_by_id():
    return {q.id: q for g in load_quizzes({}) for q in g}


def remaining_seconds(state: dict) -> float:
    return state["start"] + state["limit"] - time.time()


def score(state: dict, questions: dict) -> list[dict]:
    rows = []
    for i, qid in enumerate(state["ids"]):
        q = questions.get(qid)
        if q is None:
            continue
        chosen = set(state["answers"].get(str(i), []))
        rows.append(
            {
                "pos": i,
                "id": qid,
                "answered": bool(chosen),
                "correct": chosen == correct_set(q),
                "flagged": i in state["flags"],
                "domain": primary_domain(q),
            }
        )
    return rows


def finish(state: dict):
    if state.get("finished"):
        return
    state["finished"] = True
    state["end"] = min(time.time(), state["start"] + state["limit"])
    rows = score(state, questions_by_id())
    # only answered questions go to the review schedule; unanswered ones may never have been read
    record_answers({question_key(r["id"]): r["correct"] for r in rows if r["answered"]}, "exam")
    correct = sum(r["correct"] for r in rows)
    history = load_json(EXAM_HISTORY_FILE, [])
    history.append(
        {
            "date": datetime.now().isoformat(timespec="minutes"),
            "questions": len(rows),
            "correct": correct,
            "percent": round(correct / len(rows) * 100, 1) if rows else 0,
            "minutes": round((state["end"] - state["start"]) / 60, 1),
            "limit_minutes": round(state["limit"] / 60),
        }
    )
    save_json(EXAM_HISTORY_FILE, history)
    save_state(state)


# --------------------------------------------------------------------------- setup


def pick_questions(pool: list, n: int, balanced: bool) -> list:
    if not balanced:
        return random.sample(pool, n)
    by_domain: dict[str, list] = {}
    for q in pool:
        by_domain.setdefault(primary_domain(q), []).append(q)
    picked = []
    for domain, weight in DOMAIN_WEIGHTS.items():
        candidates = by_domain.get(domain, [])
        picked += random.sample(candidates, min(len(candidates), round(n * weight)))
    rest = [q for q in pool if q not in picked]
    picked += random.sample(rest, min(len(rest), n - len(picked)))
    random.shuffle(picked)
    return picked[:n]


def show_setup():
    progress = load_progress()
    wrong, unanswered, correct = load_quizzes(progress)
    everything = wrong + unanswered + correct
    if not everything:
        st.warning("No quizzes found in data/quizzes.jsonl")
        return

    st.markdown(
        "The real PMLE exam has **50–60 questions in 2 hours**. You can move between questions and flag "
        "them, but you only see answers at the end."
    )
    matches = section_filter(everything, key_prefix="exam_section")
    filtered = bool(st.session_state.get("exam_section_values"))
    pool = [q for q in everything if matches(q)]
    if not pool:
        st.warning("No questions match the selected sections.")
        return

    # defaults go through session state so other pages (Study by Section) can preset them
    st.session_state.exam_n = min(st.session_state.get("exam_n", 50), len(pool))
    c1, c2 = st.columns(2)
    n = c1.number_input("Questions", 1, len(pool), key="exam_n")
    if st.session_state.get("exam_minutes_for") != n:  # re-suggest the time limit when n changes
        st.session_state.exam_minutes = max(1, round(n * 2.4))
        st.session_state.exam_minutes_for = n
    minutes = c2.number_input("Time limit (minutes)", 1, 300, key="exam_minutes")
    prefer = st.radio(
        "Question choice",
        ["Random", "Prefer questions I haven't answered or got wrong"],
        horizontal=True,
        key="exam_prefer",
    )
    balanced = st.toggle(
        "Balance by exam domain (official weights)",
        value=not filtered,
        disabled=filtered,
        key="exam_balanced",
        help="Mirrors the domain mix of the real exam. Disabled when you filter by section.",
    )

    if st.button("Start exam", type="primary", icon="⏱️"):
        candidates = pool
        if prefer.startswith("Prefer"):
            weak = [q for q in pool if progress.get(q.id) is not True]
            candidates = weak if len(weak) >= n else pool
        chosen = pick_questions(candidates, int(n), balanced and not filtered)
        save_state(
            {
                "ids": [q.id for q in chosen],
                "pos": 0,
                "answers": {},
                "flags": [],
                "start": time.time(),
                "limit": int(minutes) * 60,
                "seed": random.randrange(1_000_000),
                "finished": False,
            }
        )
        st.rerun()

    show_history()


def show_history():
    history = load_json(EXAM_HISTORY_FILE, [])
    if not history:
        return
    st.markdown("### Past attempts")
    df = pd.DataFrame(history)
    if len(df) > 1:
        st.line_chart(df.set_index("date")["percent"], y_label="Score %")
    st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")


# --------------------------------------------------------------------------- exam


@st.fragment(run_every=1)
def timer():
    state = st.session_state.exam_state
    left = remaining_seconds(state)
    if left <= 0:
        finish(state)
        st.rerun(scope="app")
    mins, secs = divmod(int(left), 60)
    colour = "red" if left < 300 else "orange" if left < 900 else "blue"
    st.markdown(f"### :{colour}[⏱️ {mins // 60}:{mins % 60:02d}:{secs:02d}]")


def go(state: dict, pos: int):
    state["pos"] = max(0, min(pos, len(state["ids"]) - 1))
    save_state(state)


def toggle_flag(state: dict, pos: int):
    flags = set(state["flags"])
    flags ^= {pos}
    state["flags"] = sorted(flags)
    save_state(state)


def show_exam(state: dict, shuffle: bool):
    questions = questions_by_id()
    if remaining_seconds(state) <= 0:
        finish(state)
        st.rerun()

    n = len(state["ids"])
    pos = state["pos"]
    q = questions[state["ids"][pos]]
    answered = sum(1 for v in state["answers"].values() if v)

    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.markdown(f"### Question {pos + 1} / {n}" + ("  🚩" if pos in state["flags"] else ""))
    with c2:
        timer()
    st.progress(answered / n, text=f"Answered {answered} / {n} · flagged {len(state['flags'])}")

    with st.container(border=True):
        render_question(q)
        order = option_order(q, state["seed"], shuffle)
        picked = answer_input(q, order, key=f"exam_{state['seed']}_{pos}", default=state["answers"].get(str(pos)))
    if sorted(picked) != sorted(state["answers"].get(str(pos), [])):
        state["answers"][str(pos)] = sorted(picked)
        save_state(state)

    c1, c2, c3 = st.columns(3)
    c1.button("⬅️ Previous", on_click=go, args=(state, pos - 1), disabled=pos == 0, width="stretch", shortcut="Left")
    c2.button(
        "🚩 Unflag" if pos in state["flags"] else "🚩 Flag for review",
        on_click=toggle_flag,
        args=(state, pos),
        width="stretch",
        shortcut="F",
    )
    c3.button(
        "Next ➡️",
        on_click=go,
        args=(state, pos + 1),
        disabled=pos == n - 1,
        type="primary",
        width="stretch",
        shortcut="Right",
    )
    st.caption("Shortcuts: ← previous · → next · F flag")

    with st.expander("🗺️ Question overview", expanded=False):
        st.caption("✅ answered · 🚩 flagged · ▫️ not answered")
        per_row = 10
        for start in range(0, n, per_row):
            cols = st.columns(per_row)
            for i in range(start, min(start + per_row, n)):
                mark = "🚩" if i in state["flags"] else "✅" if state["answers"].get(str(i)) else "▫️"
                cols[i - start].button(
                    f"{mark}{i + 1}",
                    key=f"jump_{i}",
                    on_click=go,
                    args=(state, i),
                    type="primary" if i == pos else "secondary",
                    width="stretch",
                )

    st.markdown("---")
    with st.popover("🏁 Finish exam"):
        unanswered = n - answered
        if unanswered or state["flags"]:
            st.warning(f"{unanswered} unanswered and {len(state['flags'])} flagged question(s).")
        st.write("Finish now and see your results?")
        if st.button("Yes, finish", type="primary"):
            finish(state)
            st.rerun()


# --------------------------------------------------------------------------- results


def show_results(state: dict, shuffle: bool):
    questions = questions_by_id()
    rows = score(state, questions)
    if not rows:
        st.warning("The questions of this exam no longer exist.")
        if st.button("New exam"):
            save_state(None)
            st.rerun()
        return
    total = len(rows)
    correct = sum(r["correct"] for r in rows)
    pct = correct / total * 100
    used = (state["end"] - state["start"]) / 60

    if pct >= PASS_MARK:
        st.success(f"## {pct:.0f}% — looks like a pass 🎉")
    else:
        st.error(f"## {pct:.0f}% — below the ~{PASS_MARK}% target")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Correct", f"{correct} / {total}")
    c2.metric("Unanswered", sum(not r["answered"] for r in rows))
    c3.metric("Time used", f"{used:.0f} / {state['limit'] / 60:.0f} min")
    c4.metric("Per question", f"{used * 60 / total:.0f} s")
    st.caption(f"Google doesn't publish the passing score; {PASS_MARK}% is a commonly used target.")

    st.markdown("### Results by exam domain")
    df = pd.DataFrame(rows)
    by_domain = (
        df.groupby("domain")
        .agg(questions=("correct", "size"), correct=("correct", "sum"))
        .assign(score=lambda d: d["correct"] / d["questions"] * 100)
        .sort_values("score")
        .reset_index()
    )
    st.dataframe(
        by_domain,
        hide_index=True,
        width="stretch",
        column_config={
            "domain": "Exam domain",
            "score": st.column_config.ProgressColumn("Score", format="%.0f%%", min_value=0, max_value=100),
        },
    )
    weakest = by_domain.iloc[0]["domain"]
    if st.button(f"🧠 Study my weakest domain: {weakest}"):
        set_section_preset("learn_section", EXAM_DOMAIN, [weakest])
        st.session_state.learn_preset = {"mode": "🧠 Learn", "sources": ["Wrong answered", "Not answered"]}
        st.switch_page("pages/6_🎓_Learn_Mode.py")

    st.markdown("### Review")
    show = st.radio("Show", ["Wrong or unanswered", "Flagged", "All"], horizontal=True, key="exam_review_filter")
    for r in rows:
        if show == "Wrong or unanswered" and r["correct"]:
            continue
        if show == "Flagged" and not r["flagged"]:
            continue
        q = questions[r["id"]]
        icon = "✅" if r["correct"] else "❌" if r["answered"] else "⏭️"
        title = f"{icon} {r['pos'] + 1}. (#{q.id}) " + ("🚩 " if r["flagged"] else "") + r["domain"]
        with st.expander(title):
            render_question(q)
            order = option_order(q, state["seed"], shuffle)
            render_answer(q, order, chosen=set(state["answers"].get(str(r["pos"]), [])))
            question_tools(q, ctx=f"exam{r['pos']}", shortcuts=False)

    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("💾 Save results to overall progress", width="stretch", disabled=state.get("saved", False)):
        saved = load_progress()
        saved.update({r["id"]: r["correct"] for r in rows if r["answered"]})
        save_progress(saved)
        state["saved"] = True
        save_state(state)
        st.toast("Exam results merged into overall progress.")
        st.rerun()
    if c2.button("🆕 New exam", type="primary", width="stretch"):
        save_state(None)
        st.rerun()
    st.caption("Answers were already added to your review history and schedule.")


def main():
    st.set_page_config(page_title="Exam Simulation", layout="wide")
    st.title("⏱️ Exam Simulation")
    shuffle = shuffle_setting()

    state = get_state()
    if not state:
        show_setup()
    elif state.get("finished"):
        show_results(state, shuffle)
    else:
        show_exam(state, shuffle)


if __name__ == "__main__":
    main()
