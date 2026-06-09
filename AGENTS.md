# AGENTS.md — Cross-Tool Instructions

This is the **primary instruction file for every coding agent** working on this
repo (Claude Code, Codex, Antigravity, Cursor, or any other). Read it fully
before touching anything.

## Project in one line

A **personal, local-first FIFA World Cup prediction research tool** — a
disciplined research notebook with a transparent, deterministic prediction
layer. Not a SaaS, not a betting bot, not a cloud app.

## Stack

- **Python** (standard library preferred)
- **Streamlit** for the UI — runtime goal is `streamlit run app.py`
- **SQLite** at `data/worldcup.db` for storage

## Hard boundaries (do not cross)

- No cloud services, no Supabase, no Vercel, no hosting, no deployment.
- No auth, no accounts, no payments, no affiliate systems.
- No native iOS / mobile.
- No betting automation. This tool never places bets.
- No scraping of protected or paywalled sites.
- No agent swarms or speculative over-engineering.
- Division of labor: **AI structures and explains research notes; deterministic
  Python functions calculate probabilities.** Never let an LLM invent the final
  numbers.

## Read these before editing code (source of truth)

1. [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) — what this is and does
2. [`docs/BUILD_RULES.md`](docs/BUILD_RULES.md) — constraints on how to build
3. [`docs/STATUS.md`](docs/STATUS.md) — current stage, next task, known gaps
4. [`docs/DECISIONS.md`](docs/DECISIONS.md) — architectural decision log

## Before editing — checklist

- [ ] Read the four source-of-truth docs above.
- [ ] Confirm your task matches the **Next recommended task** in `STATUS.md`
      (or is explicitly requested by the human).
- [ ] Confirm the change respects every hard boundary above.
- [ ] Plan the smallest change that satisfies the task.
- [ ] Note any new assumption you are about to make.

## After editing — checklist

- [ ] Run the validation commands below; paste real output.
- [ ] Keep the diff tight — only files your task required.
- [ ] Update [`docs/STATUS.md`](docs/STATUS.md) (stage, completed, next task,
      known gaps, last updated date).
- [ ] If you made an architectural choice, add a row to
      [`docs/DECISIONS.md`](docs/DECISIONS.md).
- [ ] Fill out [`docs/HANDOFF_TEMPLATE.md`](docs/HANDOFF_TEMPLATE.md) in your
      final message so the next agent can continue cleanly.

## Validation commands

```bash
# Initialize / verify the database schema
python src/db.py

# Inspect the schema
sqlite3 data/worldcup.db ".schema"

# Byte-compile all Python to catch syntax errors
python -m compileall src

# Run the app (once app.py exists)
streamlit run app.py
```

## Operating rules

- **One task per session.** Do not bundle unrelated work.
- **Keep scope tight.** Do not "improve" adjacent code, reformat files, or
  refactor things that are not broken.
- **Prefer pure functions** for odds math, prediction blending, and scoring so
  they are testable and inspectable.
- **Prediction math must be transparent and deterministic** — same inputs always
  produce the same outputs.
- **Document every new assumption** in your handoff and, if structural, in
  `DECISIONS.md`.
- **Ask before large rewrites** or anything that crosses a hard boundary.
- After meaningful work, **update `STATUS.md`**. This is non-optional — it is how
  the next tool stays in sync.
