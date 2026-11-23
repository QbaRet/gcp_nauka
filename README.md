# Quiz Learner — for Google Cloud Professional Machine Learning Engineer Certification (PMLE)

## Description

This is a Streamlit application designed to help users prepare for the Google Cloud Professional Machine Learning Engineer (PMLE) certification exam. The app provides a quiz interface and around 850 questions.

By going though all these questions, users can reinforce their understanding of key concepts and topics covered in the PMLE exam. Wrong answers are tracked to help users focus on areas where they need improvement. You can retry wrong answers until you master them.

![App Usage](./_docs/assets/app_usage.gif)

## Installation

Clone the repository locally:

```bash
git clone git@github.com:AndyTheFactory/gcp-pmle-quiz.git
cd gcp-pmle-quiz
```

### Docker

Build the Docker image:

```bash
docker compose up --build -d
```

### Using `uv`

Install `uv` (more info [here](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer))

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install dependencies and run the app:

```bash
uv sync
```

Run the app locally:

```bash
uv run streamlit run 🏠_Dashboard.py
```


### Good old `pip`

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install pip-tools
python -m piptools compile \
    -o requirements.txt \
    pyproject.toml
pip install -r requirements.txt
```

Run the app locally:

```bash
python  -m streamlit run 🏠_Dashboard.py
```
## Usage

Open your browser and go to `http://localhost:8501`

To start a new quiz session, navigate to "Quiz Mode" from the sidebar.

Click Start round and answer questions.

When you finished a round, you can press "Stop Round" and save your progress.

It is important to save your progress in order to assess your knowledge in specific topics.
Check your knowledge gap in the "Dashboard" tab.

If you want to use Notebook LM to help you prepping for the Certification exam, you can export a markdown file with all the questions you got wrong, and use it as a source for Notebook LM. Prompt then Notebook LM to create quizzes and flashcards based on these questions. You can use a prompt like this:

```

Create a quiz that relies on questions i answered incorrectly. Use those questions and answers as templates to create more quizz questions.
Base your questions also on the best practice documents provided
```

## Study modes

- **📖 Theory** — 15 topic lessons following the PMLE exam domains (choosing an approach, BigQuery ML,
  AI APIs, generative AI, data storage & processing, Feature Store, notebooks & experiments, custom and
  distributed training, ML fundamentals, serving, pipelines & MLOps, monitoring, security & responsible AI).
  Each lesson has decision tables ("X vs Y"), exam traps, key takeaways and links to the Google Cloud docs
  it was checked against. Mark lessons as read, keep notes, search all lessons, review all cheat sheets on
  one tab, and press **Practice** to study the questions linked to the lesson. Lessons live in `theory/`
  (`lessons.json` + one Markdown file per lesson) and can be edited.
- **📚 Study by Section** — a table of all sections with how much you've seen, accuracy, readiness, mastery and
  questions due for review. Select one or more sections (or let it pick your 3 weakest) and jump straight into
  Learn, Flashcards, a review of due questions, a Quiz round or a 20-question mini exam.
  Section types: the six official **exam domains** (assigned from question tags, approximate), GCP topics,
  ML topics and GCP products. Tags that differ only in case are merged.
- **🎓 Learn Mode** (Quizlet-style)
  - *Flashcards*: flip the card, rate yourself "Know it" / "Still learning".
  - *Learn*: answer the question; missed cards come back a few cards later until you get them right.
  - Decks: exam questions (wrong / not answered / correct / due for review / bookmarked, filterable by section)
    or **GCP products** ("which product is this?", built from `data/gcp_products.jsonl`).
- **⏱️ Exam Simulation** — timed (default 50 questions / 2 h), no feedback until the end, flag questions for
  review, question overview, domain-balanced question mix. Results by exam domain, full review, and a history of
  past attempts.
- **Spaced repetition** — every answer (quiz, learn, exam) goes into a review schedule (simplified SM-2).
  "📅 Due for review" sets show what to repeat today; the dashboard shows the count.
- **Shuffled answer options** (sidebar toggle) — so you learn the content, not "the answer is D". The
  explanation's letters refer to the original order; a mapping is shown below the answer.
- **Bookmarks, notes and answer history** for every question (☆ button and "📝 Note & history").
- **Keyboard shortcuts** — Quiz: Enter submit, → next. Flashcards: Space flip, 1 / 2 rate. Learn: Enter check /
  continue, D "I don't know". Exam: ← / → navigate, F flag. B bookmarks the current question.

## Some details

Data files:
- `data/quizzes.jsonl`: quiz items (one JSON object per line) with fields: `question` (str), `options` (list[str]), `answer` (int index), `explanation` (str).
- `data/progress.json`: autogenerated to store your progress (which questions were answered correct/wrong).
- `data/study.json`: answer history and spaced-repetition schedule (autogenerated).
- `data/notes.json`: bookmarks and personal notes (autogenerated).
- `data/exam_history.json`: exam simulation results (autogenerated).
- `data/theory_progress.json`: lessons marked as read and lesson notes (autogenerated).
- `theory/`: theory lessons (`lessons.json` holds order, exam domains, question-matching rules and sources).

Usage:
- Main page shows stats (total, unanswered, correct, wrong).
- Press `Start` to begin asking questions selected randomly from unanswered and previously-wrong questions.
- After submitting an answer, feedback and the explanation are shown and progress is saved.
- Press `Reset progress` to clear your progress.
