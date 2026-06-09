# Status

> Single source of truth for "where we are." Update this after any meaningful
> work — it is how every tool (Claude Code, Codex, Antigravity, …) stays in sync.

**Last updated:** 2026-06-10

## Current stage

Core math layer, manual SQLite persistence, and post-match prediction scoring/persistence are complete. Wires a Streamlit UI allowing the user to view recent saved predictions, record actual match result outcomes (`home`/`draw`/`away`), score predictions against the bookmaker baseline using Brier score and log loss, and view scored prediction history. Idempotent schema migrations add nullable scoring columns to the `predictions` table.

## GitHub connection status

- **Status:** Connected to GitHub
- **Repository URL:** [worldcup-prediction-tool](https://github.com/buildrr89/worldcup-prediction-tool)
- **Visibility:** Private
- **Latest pushed commit:** `85084ac` ("Initial local-first World Cup prediction tool")
- **Branch:** `main`
- **Public release:** Pending (license not chosen yet)

## Completed files

- Governance docs: `AGENTS.md`, `CLAUDE.md`, `README.md`,
  `docs/PROJECT_BRIEF.md`, `docs/BUILD_RULES.md`, `docs/STATUS.md`,
  `docs/DECISIONS.md`, `docs/HANDOFF_TEMPLATE.md`.
- `src/db.py` — SQLite foundation (connection helper + `init_db()`) plus
  manual persistence helpers: `create_match`, `create_signal`,
  `create_factor`, `create_prediction`, `save_prediction_flow` (single
  transaction, no partial saves), `list_recent_predictions`,
  `get_prediction_for_scoring`, `score_prediction`,
  `list_unscored_predictions`, and `list_scored_predictions`. Idempotent
  `ensure_column` guards are run in `init_db` to append the 8 nullable scoring columns.
- `tests/test_db.py` — 21 `unittest` tests for the persistence and migration layer, each
  against a `tempfile.TemporaryDirectory` DB: table creation, creation helpers, flow persistence
  with rollback, prediction loading for scoring, actual scoring computation and updating,
  unscored/scored lists filters, and validation exceptions. All passing.
- `src/odds.py` — odds de-vig math layer (pure function
  `decimal_odds_to_implied_probabilities`). Completed — converts 1X2
  decimal odds to de-vigged baseline probabilities; validates inputs and
  raises `ValueError` for non-numeric or `<= 1.0` odds.
- `tests/test_odds.py` — 5 `unittest` tests for the odds layer (normal market,
  heavy favourite, sum-to-1.0, invalid odds, non-numeric odds). All passing.
- `src/predictor.py` — deterministic predictor/blending math layer (pure
  function `blend_probabilities`). Completed — takes a de-vigged baseline
  plus a list of research factors and produces a final home/draw/away
  probability. Each factor nudges one outcome by
  `magnitude * weight * max_total_shift` (added if `positive`, subtracted if
  `negative`); outcomes are clamped to a 0.001 minimum and renormalised to ~1.0.
  Returns `baseline`, `applied_factors`, `max_total_shift`, and a plain-English
  `explanation`. Validates baseline keys/types/sum, `max_total_shift` range, and
  every factor field, raising `ValueError` on bad input. The bookmaker baseline
  is the anchor; factors only nudge it.
- `tests/test_predictor.py` — 15 `unittest` tests for the predictor layer
  (no-factor passthrough, None-as-empty, positive/negative nudges, sum-to-1.0,
  multiple-factor normalisation, extreme-shift clamping, and all validation
  failure modes). All passing.
- `src/scoring.py` — scoring/evaluation math layer (pure functions
  `validate_probabilities`, `actual_result_to_one_hot`, `brier_score`,
  `log_loss`, `compare_prediction_to_baseline`). Completed — judges a
  predicted home/draw/away distribution against the actual outcome using two
  proper scoring rules. Brier score is the summed squared error vs the one-hot
  outcome (perfect = 0.0); log loss is `-log(p)` of the actual outcome's
  probability, clamped to `[epsilon, 1 - epsilon]`. `compare_prediction_to_baseline`
  scores prediction and baseline against the same result and reports the deltas
  plus improvement booleans (True when the prediction's score is lower).
  Standard library only; validates inputs and raises `ValueError` on bad input.
- `tests/test_scoring.py` — 12 `unittest` tests for the scoring layer
  (probability validation pass/missing-key/bad-sum, one-hot values and invalid
  result, perfect Brier = 0.0, worse-vs-better Brier ordering, good-vs-bad log
  loss ordering, invalid epsilon, comparison key set, and improvement/no-
  improvement marking). All passing.
- `app.py` — Streamlit shell. Completed. Supports match creation, bookmaker de-vig calculation,
  factor blending, manual flow saving, and post-match scoring of saved predictions.
  Has dedicated "Score saved prediction" selectbox controls and a "Recent scored predictions" table.
- `requirements.txt` — Completed. Single dependency: `streamlit`. (Standard
  library covers everything else.)
- Public-repo readiness docs — Completed. `README.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `LICENSE_RECOMMENDATION.md` (MIT recommended, decision pending), and
  `docs/PUBLIC_REPO_READINESS.md` (checklist).

## Current database status

**Initialized.** `data/worldcup.db` exists with the five core tables created by
`src/db.py`:

- `teams` — name, fifa_code
- `matches` — home/away teams, kickoff, stage, status, scores
- `signals` — bookmaker decimal odds + implied probabilities per match
- `factors` — research factors (type, direction, magnitude, confidence, note)
- `predictions` — blended home/draw/away probabilities + reasoning JSON + actual result outcome + Brier & log-loss evaluation scores

## Next recommended task

**Add Football-Data.co.uk CSV import for historical results and odds backtesting.**

## Validation commands

```bash
python3 src/db.py                       # idempotent: re-creates missing tables and applies schema updates
sqlite3 data/worldcup.db ".schema"      # confirm the tables and columns exist
python3 -m compileall src app.py        # catch syntax errors
python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py tests/test_db.py  # run all 53 tests
streamlit run app.py                    # launch the app
```

**Last run (2026-06-10, Result entry + scoring persistence session):**
`python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py tests/test_db.py` →
`Ran 53 tests in 0.120s` / `OK` (all 53 passing — 5 odds + 15 predictor +
12 scoring + 21 db).
`python3 -m compileall src app.py` → compiled, no errors.

## Known gaps

- The app was **not run interactively** in the build environment (Streamlit
  not installed there); the widgets are verified via `compileall` and database functions,
  but run `streamlit run app.py` locally to confirm UI flow behaves correctly.
- Factor `weight` is stored inside `factors.note` text, not a dedicated column.
- No edit/delete of saved predictions yet.
- Factors are limited to 3 fixed rows.
- No AI note → factor parser yet.
- Actual `LICENSE` file not yet chosen/added.
