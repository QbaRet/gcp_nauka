"""Quizlet-style study mode: flashcards and an adaptive "Learn" mode.

Two decks:
- Exam questions (filterable by section, wrong/unanswered/due/bookmarked)
- GCP products from data/gcp_products.jsonl ("which product is this?")

Modes:
- Flashcards: flip a card, then mark it as "Know it" or "Still learning".
- Learn: answer the question; missed cards come back a few cards later until you get them right.

Every first attempt of a card in a session is written to the answer history and the spaced-repetition
schedule. The session itself is kept in the disk cache, so it survives a page reload.
"""

import random
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from models.questions import Question
from utils import (
    DATA_DIR,
    load_progress,
    load_quizzes,
    save_progress,
    section_filter,
    set_css_style,
)
from utils.session import cache
from utils.study import (
    answer_input,
    due_question_ids,
    is_due,
    load_study,
    option_labels,
    option_order,
    product_key,
    question_key,
    question_tools,
    record_answer,
    render_answer,
    render_question,
    shuffle_setting,
    starred_ids,
)

CACHE_KEY = "learn_state"
STATE_VERSION = 2
REQUEUE_GAP = 3  # a missed card comes back after this many other cards

DECK_QUESTIONS, DECK_PRODUCTS = "questions", "products"
DECKS = {"📝 Exam questions": DECK_QUESTIONS, "☁️ GCP products": DECK_PRODUCTS}
MODES = {"🃏 Flashcards": "flashcards", "🧠 Learn": "learn"}

QUESTION_SOURCES = ["Wrong answered", "Not answered", "Answered correctly", "📅 Due for review", "⭐ Bookmarked"]
PRODUCT_SOURCES = ["All", "📅 Due for review", "🆕 Not studied yet"]

set_css_style(Path("style.css"))


# --------------------------------------------------------------------------- cards


@dataclass
class Card:
    key: str  # study key, see utils.study.question_key / product_key
    question: Question  # products are wrapped into a synthetic single-choice question
    back_md: str | None = None  # extra content for the back of product cards
    is_product: bool = False
    title: str = ""


def load_products() -> dict[str, dict]:
    path = DATA_DIR / "gcp_products.jsonl"
    if not path.exists():
        return {}
    return {p["product_name"]: p for p in pd.read_json(path, lines=True).to_dict(orient="records")}


def mask_name(text: str, name: str) -> str:
    """Hide the product name (and its 'Cloud '/'Google '/'Gemini Enterprise ' stripped form) in the description."""
    variants = {name, re.sub(r"^(Google Cloud|Google|Cloud|Gemini Enterprise)\s+", "", name)}
    for v in sorted(variants, key=len, reverse=True):
        if len(v) > 2:
            text = re.sub(re.escape(v), "▢▢▢", text, flags=re.IGNORECASE)
    return text


def product_card(name: str, products: dict[str, dict], seed) -> Card:
    p = products[name]
    rng = random.Random(f"{seed}-{name}")
    same_type = [n for n, o in products.items() if n != name and o.get("entity_type") == p.get("entity_type")]
    others = [n for n in products if n != name and n not in same_type]
    rng.shuffle(same_type)
    rng.shuffle(others)
    distractors = (same_type + others)[:3]
    options = distractors + [name]
    rng.shuffle(options)

    use_cases = "".join(f"\n- {u}" for u in p.get("use_cases", []))
    prompt = f"**Which Google Cloud product is this?**\n\n{mask_name(p.get('short_description', ''), name)}"
    if use_cases:
        prompt += f"\n\n*Typical use cases:*{mask_name(use_cases, name)}"

    back = [f"**{name}** · *{p.get('entity_type', '')}*", "", p.get("short_description", "")]
    if p.get("use_cases"):
        back += ["", "**Use it for:**"] + [f"- {u}" for u in p["use_cases"]]
    if p.get("not_used_when"):
        back += ["", "**Don't use it when:**"] + [f"- {u}" for u in p["not_used_when"]]
    if p.get("connected_to"):
        back += ["", "**Works with:** " + ", ".join(p["connected_to"])]

    q = Question(
        id=0,
        mode="single_choice",
        question=prompt,
        options=options,
        answer=options.index(name),
    )
    return Card(key=product_key(name), question=q, back_md="\n".join(back), is_product=True, title=name)


def build_card(key: str, questions: dict[int, Question], products: dict[str, dict], seed) -> Card | None:
    if key.startswith("p:"):
        name = key[2:]
        return product_card(name, products, seed) if name in products else None
    q = questions.get(int(key))
    return Card(key=key, question=q, title=f"Question #{q.id}") if q else None


# --------------------------------------------------------------------------- state


def get_state() -> dict | None:
    if "learn_state" not in st.session_state:
        state = cache.get(CACHE_KEY)
        st.session_state.learn_state = state if state and state.get("version") == STATE_VERSION else None
    return st.session_state.learn_state


def set_state(state: dict | None):
    st.session_state.learn_state = state
    if state is None:
        cache.delete(CACHE_KEY)
    else:
        cache.set(CACHE_KEY, state)


def reset_card_ui():
    st.session_state.learn_revealed = False
    st.session_state.learn_result = None
    st.session_state.learn_chosen = None


def start_session(mode: str, deck: str, keys: list[str]):
    keys = list(keys)
    random.shuffle(keys)
    set_state(
        {
            "version": STATE_VERSION,
            "mode": mode,
            "deck": deck,
            "queue": keys,
            "total": len(keys),
            "mastered": [],
            "misses": {},  # key -> how many times missed / marked "still learning"
            "first_try": {},  # key -> result of the first attempt
            "step": 0,  # bumps on every card, used to reset widget state
            "seed": random.randrange(1_000_000),
        }
    )
    reset_card_ui()
    st.session_state.learn_summary_shown = False


def record(state: dict, key: str, ok: bool):
    """Move the current card: mastered when ok, otherwise re-queue it a few cards later."""
    if key not in state["first_try"]:
        state["first_try"][key] = ok
        record_answer(key, ok, f"learn-{state['mode']}")
    state["queue"].pop(0)
    if ok:
        state["mastered"].append(key)
    else:
        state["misses"][key] = state["misses"].get(key, 0) + 1
        state["queue"].insert(min(REQUEUE_GAP, len(state["queue"])), key)
    state["step"] += 1
    set_state(state)
    reset_card_ui()


# --------------------------------------------------------------------------- screens


def render_progress(state: dict):
    mastered = len(state["mastered"])
    total = state["total"]
    still_learning = len(set(state["misses"]) - set(state["mastered"]))
    st.progress(mastered / total if total else 1.0, text=f"Mastered {mastered} / {total}")
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Mastered", mastered)
    c2.metric("🔁 Still learning", still_learning)
    c3.metric("🆕 Not seen yet", total - mastered - still_learning)


def question_pool(sources: list[str]) -> list[str]:
    progress = load_progress()
    wrong, unanswered, correct = load_quizzes(progress)
    everything = wrong + unanswered + correct
    matches = section_filter(everything, key_prefix="learn_section")
    selected: dict[int, Question] = {}
    for src, group in (("Wrong answered", wrong), ("Not answered", unanswered), ("Answered correctly", correct)):
        if src in sources:
            selected.update({q.id: q for q in group})
    if "📅 Due for review" in sources:
        due = due_question_ids(progress)
        selected.update({q.id: q for q in everything if q.id in due})
    if "⭐ Bookmarked" in sources:
        stars = starred_ids()
        selected.update({q.id: q for q in everything if q.id in stars})
    return [question_key(q.id) for q in selected.values() if matches(q)]


def product_pool(sources: list[str]) -> list[str]:
    products = load_products()
    study = load_study()
    types = sorted({p.get("entity_type", "") for p in products.values()})
    chosen_types = st.multiselect("Product types (empty = all)", types, key="learn_product_types")
    names = [n for n, p in products.items() if not chosen_types or p.get("entity_type") in chosen_types]
    if "All" in sources:
        return [product_key(n) for n in names]
    keep = set()
    if "📅 Due for review" in sources:
        keep |= {n for n in names if is_due(study.get(product_key(n)))}
    if "🆕 Not studied yet" in sources:
        keep |= {n for n in names if product_key(n) not in study}
    return [product_key(n) for n in names if n in keep]


def show_setup():
    preset = st.session_state.pop("learn_preset", None)
    if preset:
        st.session_state.learn_mode = preset.get("mode", st.session_state.get("learn_mode"))
        st.session_state.learn_deck = "📝 Exam questions"
        st.session_state.learn_sources = preset.get("sources", QUESTION_SOURCES[:3])

    c1, c2 = st.columns(2)
    mode_label = c1.radio("Study mode", list(MODES), horizontal=True, key="learn_mode")
    deck_label = c2.radio("Deck", list(DECKS), horizontal=True, key="learn_deck")
    mode, deck = MODES[mode_label], DECKS[deck_label]
    if mode == "flashcards":
        st.caption("Read the card, flip it and rate yourself. Cards you don't know come back.")
    else:
        st.caption("Answer each card. Missed cards come back a few cards later until you get them right.")

    if deck == DECK_QUESTIONS:
        st.session_state.setdefault("learn_sources", ["Wrong answered", "Not answered"])
        sources = st.multiselect("Questions to study", QUESTION_SOURCES, key="learn_sources")
        pool = question_pool(sources)
    else:
        st.session_state.setdefault("learn_product_sources", ["All"])
        sources = st.multiselect("Products to study", PRODUCT_SOURCES, key="learn_product_sources")
        pool = product_pool(sources)

    if not pool:
        st.warning("No cards match the selected filters.")
        return

    if len(pool) > 1:
        size = st.slider("Cards in this session", 1, len(pool), min(20, len(pool)), key="learn_size")
    else:
        size = 1
    st.caption(f"{len(pool)} cards match the filters.")

    if st.button("Start studying", type="primary", icon="🎓", shortcut="Enter"):
        start_session(mode, deck, random.sample(pool, size))
        st.rerun()


def show_flashcard(state: dict, card: Card):
    q = card.question
    with st.container(border=True):
        if card.is_product:
            st.caption("GCP product")
            st.markdown(f"## {card.title}")
            st.caption(load_products()[card.title].get("entity_type", ""))
        else:
            st.caption(card.title + (" · multiple answers" if q.mode == "multiple_choice" else ""))
            render_question(q)
            order = option_order(q, state["seed"], st.session_state.shuffle_now)
            labels = option_labels(q, order)
            if not st.session_state.learn_revealed:  # once revealed, render_answer shows the options
                for o in order:
                    with st.container(border=True):
                        st.markdown(labels[o])
        if st.session_state.learn_revealed:
            st.divider()
            if card.is_product:
                st.markdown(card.back_md)
            else:
                render_answer(q, order)

    if not st.session_state.learn_revealed:
        if st.button("🔄 Flip card", type="primary", width="stretch", shortcut="Space"):
            st.session_state.learn_revealed = True
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        if c1.button("🔁 Still learning", width="stretch", shortcut="1"):
            record(state, card.key, False)
            st.rerun()
        if c2.button("✅ Know it", type="primary", width="stretch", shortcut="2"):
            record(state, card.key, True)
            st.rerun()
    st.caption(
        "Shortcuts: Space = flip · 1 = still learning · 2 = know it" + ("" if card.is_product else " · B = bookmark")
    )


def show_learn_card(state: dict, card: Card):
    q = card.question
    key = f"learn_choice_{state['step']}"
    answered = st.session_state.learn_result is not None
    order = (
        list(range(len(q.options))) if card.is_product else option_order(q, state["seed"], st.session_state.shuffle_now)
    )

    with st.container(border=True):
        missed = state["misses"].get(card.key)
        st.caption(("GCP product" if card.is_product else card.title) + (f" · missed {missed}×" if missed else ""))
        if card.is_product:
            st.markdown(q.question)  # plain markdown, not the HTML used by exam questions
        else:
            render_question(q)
        picked = answer_input(q, order, key=key, disabled=answered)

    if not answered:
        c1, c2 = st.columns(2)
        if c1.button("✅ Check", type="primary", width="stretch", shortcut="Enter"):
            if not picked:
                st.warning("Please select an answer first.")
            else:
                st.session_state.learn_chosen = picked
                st.session_state.learn_result = picked == ({q.answer} if isinstance(q.answer, int) else set(q.answer))
                st.rerun()
        if c2.button("🤷 I don't know", width="stretch", shortcut="D"):
            st.session_state.learn_chosen = set()
            st.session_state.learn_result = False
            st.rerun()
        st.caption("Shortcuts: Enter = check · D = I don't know" + ("" if card.is_product else " · B = bookmark"))
        return

    if st.session_state.learn_result:
        st.success("Correct! ✅")
    else:
        st.error("Not quite — this card will come back a few cards later. ❌")
    if card.is_product:
        render_answer(q, order, chosen=st.session_state.learn_chosen, explanation=False)
        with st.expander("About this product", expanded=True):
            st.markdown(card.back_md)
    else:
        render_answer(q, order, chosen=st.session_state.learn_chosen)
    if st.button("➡️ Continue", type="primary", width="stretch", shortcut="Enter"):
        record(state, card.key, st.session_state.learn_result)
        st.rerun()


def show_summary(state: dict, cards: dict[str, Card]):
    if not st.session_state.get("learn_summary_shown"):
        st.balloons()
        st.session_state.learn_summary_shown = True

    total = state["total"]
    first_ok = sum(1 for v in state["first_try"].values() if v)
    st.success(f"Session complete — all {total} cards mastered! 🎉")
    st.markdown(f"Known on the first try: **{first_ok} / {total}** ({first_ok / total * 100:.0f}%)")
    st.caption(
        f"Results were added to your review schedule — {date.today():%d.%m}: "
        "cards you knew come back in a few days, the ones you missed tomorrow."
    )

    hard = sorted(state["misses"].items(), key=lambda kv: -kv[1])
    if hard:
        st.markdown("#### Hardest cards")
        for key, n in hard[:10]:
            card = cards.get(key)
            if card is None:
                continue
            text = card.title if card.is_product else re.sub(r"<[^>]+>", "", card.question.question)
            st.markdown(f"- **{card.title}** (missed {n}×) — {text[:120]}{'…' if len(text) > 120 else ''}")

    c1, c2, c3 = st.columns(3)
    if hard and c1.button("🔁 Study hardest again", width="stretch"):
        start_session(state["mode"], state["deck"], [k for k, _ in hard])
        st.rerun()
    can_save = state["mode"] == "learn" and state["deck"] == DECK_QUESTIONS
    if can_save and c2.button("💾 Save to progress", width="stretch"):
        saved = load_progress()
        saved.update({int(k): v for k, v in state["first_try"].items()})
        save_progress(saved)
        st.toast("First-try results merged into overall progress.")
    if c3.button("🆕 New session", type="primary", width="stretch", shortcut="Enter"):
        set_state(None)
        st.rerun()

    if can_save:
        st.caption("“Save to progress” records each card's first-try result, the same way Quiz Mode does.")


def show_session(state: dict):
    questions = {q.id: q for g in load_quizzes({}) for q in g}
    products = load_products() if state["deck"] == DECK_PRODUCTS else {}
    # drop cards that no longer exist (e.g. edited data file)
    state["queue"] = [k for k in state["queue"] if build_card(k, questions, products, state["seed"])]

    if not state["queue"]:
        keys = set(state["first_try"]) | set(state["misses"])
        cards = {k: c for k in keys if (c := build_card(k, questions, products, state["seed"]))}
        show_summary(state, cards)
        return

    render_progress(state)
    card = build_card(state["queue"][0], questions, products, state["seed"])
    if state["mode"] == "flashcards":
        show_flashcard(state, card)
    else:
        show_learn_card(state, card)

    if not card.is_product:
        question_tools(card.question, ctx="learn")

    st.markdown("---")
    with st.popover("🚫 End session"):
        st.warning("Cards you already answered stay in your history; the rest of this session is dropped.")
        if st.button("Yes, end it", type="primary"):
            set_state(None)
            st.rerun()


def main():
    st.set_page_config(page_title="Learn Mode")
    st.title("🎓 Learn Mode")
    st.session_state.shuffle_now = shuffle_setting()
    st.session_state.setdefault("learn_revealed", False)
    st.session_state.setdefault("learn_result", None)
    st.session_state.setdefault("learn_chosen", None)

    state = get_state()
    if state:
        show_session(state)
    else:
        show_setup()


if __name__ == "__main__":
    main()
