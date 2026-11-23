"""Theory lessons: loading, linking lessons to practice questions, and reading progress.

Lessons live in ``theory/``: ``lessons.json`` holds the metadata (order, title, exam domains, how to match
practice questions, sources) and ``<id>.md`` the lesson text. Reading progress and lesson notes are stored
in ``data/theory_progress.json``.

Markdown conventions inside a lesson:
- ``## ⚖️ ...`` sections are decision guides / cheat sheets (also collected on the "Cheat sheets" tab)
- ``## 🪤 ...`` sections list exam traps
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

from models.questions import Question
from utils import DATA_DIR

THEORY_DIR = Path("theory")
INDEX_FILE = THEORY_DIR / "lessons.json"
THEORY_PROGRESS_FILE = DATA_DIR / "theory_progress.json"
CHEAT_SHEET_MARK = "⚖️"


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    domains: tuple[str, ...]
    minutes: int
    summary: str
    products: tuple[str, ...] = field(default_factory=tuple)  # substrings matched against product tags
    topics: tuple[str, ...] = field(default_factory=tuple)  # substrings matched against GCP/ML topic tags
    sources: tuple[tuple[str, str], ...] = field(default_factory=tuple)  # (title, url)

    @property
    def path(self) -> Path:
        return THEORY_DIR / f"{self.id}.md"

    def body(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.exists() else "_Lesson text is missing._"


def _mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


@lru_cache(maxsize=4)
def _load(index_mtime: float) -> tuple[Lesson, ...]:
    if not INDEX_FILE.exists():
        return ()
    raw = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return tuple(
        Lesson(
            id=item["id"],
            title=item["title"],
            domains=tuple(item.get("domains", [])),
            minutes=int(item.get("minutes", 10)),
            summary=item.get("summary", ""),
            products=tuple(p.lower() for p in item.get("match", {}).get("products", [])),
            topics=tuple(t.lower() for t in item.get("match", {}).get("topics", [])),
            sources=tuple((s["title"], s["url"]) for s in item.get("sources", [])),
        )
        for item in raw["lessons"]
    )


def load_lessons() -> list[Lesson]:
    return list(_load(_mtime(INDEX_FILE)))


def lesson_by_title(title: str) -> Lesson | None:
    return next((lesson for lesson in load_lessons() if lesson.title == title), None)


# --------------------------------------------------------------------------- linking to questions


def matches_lesson(lesson: Lesson, q: Question) -> bool:
    from utils.sections import match_form

    products = [match_form(t) for t in q.gcp_products or []]
    topics = [match_form(t) for t in (q.gcp_topics or []) + (q.ml_topics or [])]
    return any(p in t for p in lesson.products for t in products) or any(k in t for k in lesson.topics for t in topics)


def question_lessons(q: Question) -> list[str]:
    """Titles of the lessons a question practises."""
    return [lesson.title for lesson in load_lessons() if matches_lesson(lesson, q)]


# --------------------------------------------------------------------------- markdown helpers


def split_sections(markdown: str) -> list[tuple[str, str]]:
    """Split a lesson into (## heading, body) pairs; text before the first heading gets heading ''."""
    parts = re.split(r"^## +(.+)$", markdown, flags=re.MULTILINE)
    sections = [("", parts[0].strip())] if parts[0].strip() else []
    sections += [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]
    return sections


def cheat_sheets(lesson: Lesson) -> list[tuple[str, str]]:
    return [(h, b) for h, b in split_sections(lesson.body()) if h.startswith(CHEAT_SHEET_MARK)]


# --------------------------------------------------------------------------- reading progress


def load_theory_progress() -> dict[str, dict]:
    from utils.study import load_json

    return load_json(THEORY_PROGRESS_FILE, {})


def _update(lesson_id: str, **fields):
    from utils.study import save_json

    progress = load_theory_progress()
    entry = progress.setdefault(lesson_id, {})
    entry.update(fields)
    if not entry.get("read") and not entry.get("note"):
        progress.pop(lesson_id)
    save_json(THEORY_PROGRESS_FILE, progress)


def set_read(lesson_id: str, read: bool):
    _update(lesson_id, read=date.today().isoformat() if read else None)


def set_note(lesson_id: str, note: str):
    _update(lesson_id, note=note.strip())


def read_count() -> tuple[int, int]:
    lessons = load_lessons()
    progress = load_theory_progress()
    return sum(1 for lesson in lessons if progress.get(lesson.id, {}).get("read")), len(lessons)
