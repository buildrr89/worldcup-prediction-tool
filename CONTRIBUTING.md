# Contributing

Thanks for your interest in this project. It is a **personal, local-first FIFA
World Cup prediction research tool**, and contributions are welcome as long as
they respect that scope.

## Before you start

1. Read [AGENTS.md](AGENTS.md) — the primary instructions for working on this
   repo.
2. Read the source-of-truth docs: [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md),
   [docs/BUILD_RULES.md](docs/BUILD_RULES.md), [docs/STATUS.md](docs/STATUS.md),
   and [docs/DECISIONS.md](docs/DECISIONS.md).
3. Confirm your change matches the **Next recommended task** in `STATUS.md`, or
   is something the maintainer has explicitly asked for.

## Scope rules

These are hard boundaries — please do not cross them:

- **Keep it local-first.** Python + Streamlit + SQLite, runnable offline with
  `streamlit run app.py`.
- **One focused change at a time.** Each PR should be small, atomic, and
  reversible. Don't bundle unrelated work or "improve" adjacent code.
- **No cloud dependencies** (no hosting, Supabase, Vercel, remote APIs, auth,
  payments) unless the maintainer has approved it and it is logged in
  `docs/DECISIONS.md`.
- **No scraping of protected or paywalled websites.**
- **No secrets or API keys** in code, commits, logs, or screenshots.
- **No committing the generated local database** (`data/worldcup.db`) or any
  `__pycache__/` artifacts.
- **No claims that the model beats the bookmakers.** Framing stays honest:
  disciplined research, not a guaranteed edge.
- **Keep the number path deterministic.** Odds math, blending, and scoring must
  produce the same output for the same input. AI may structure research notes,
  but it must never compute or invent the final probabilities.

## Run the tests before submitting

```bash
python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py
python3 -m compileall src app.py
```

If you touched the persistence layer, also run `tests/test_db.py`.

## Branch naming

Use short, descriptive branch names, for example:

- `feature/result-entry`
- `fix/devig-rounding`
- `docs/update-status`
- `test/scoring-edge-cases`

## Checklist before opening a PR

- [ ] Change is small and focused on a single task.
- [ ] No cloud, auth, payments, or scraping introduced.
- [ ] No secrets, API keys, or `.env` committed.
- [ ] No generated DB (`data/worldcup.db`) or `__pycache__/` committed.
- [ ] Tests run and pass (paste real output in the PR).
- [ ] `python3 -m compileall src app.py` is clean.
- [ ] `docs/STATUS.md` updated if the work was meaningful.
- [ ] A row added to `docs/DECISIONS.md` if you made a structural choice.
- [ ] No claims about beating bookmakers or guaranteed predictions.
