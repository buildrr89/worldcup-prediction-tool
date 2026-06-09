# Status

> Single source of truth for "where we are." Update this after any meaningful
> work — it is how every tool (Claude Code, Codex, Antigravity, …) stays in sync.

**Last updated:** 2026-06-10

## Current stage

Core math layer complete, a Streamlit shell is wired on top of it, **and manual
SQLite persistence now works.** The database foundation exists, the odds de-vig
layer, the deterministic predictor/blending layer, and the scoring/evaluation
layer are all built and tested. `app.py` lets the owner enter odds and factors,
see baseline + blended probabilities, **and explicitly save the full flow
(match, signal, factors, prediction) to the local DB via a dedicated button.**
Saved predictions are listed back in the app.

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
- `src/db.py` — SQLite foundation (connection helper + `init_db()`) **plus
  manual persistence helpers**: `create_match`, `create_signal`,
  `create_factor`, `create_prediction`, `save_prediction_flow` (single
  transaction, no partial saves), and `list_recent_predictions`. All use
  parameterized SQL and standard-library `sqlite3` only; `create_*` helpers
  accept an optional shared `conn`. `get_connection()` now mkdirs
  `DB_PATH.parent` (reading `DB_PATH` at call time) so tests can point it at a
  temp DB by monkeypatching `db.DB_PATH`. No schema change: factor `weight` is
  preserved inside `factors.note` (see `DECISIONS.md`).
- `tests/test_db.py` — 13 `unittest` tests for the persistence layer, each
  against a `tempfile.TemporaryDirectory` DB (never touches
  `data/worldcup.db`): table creation, `create_match`/`create_signal`/
  `create_factor`/`create_prediction` round-trips, `save_prediction_flow`
  (incl. rollback on bad input), `list_recent_predictions` ordering, and
  invalid-name / invalid-match-id `ValueError`s. All passing.
- `src/odds.py` — odds de-vig math layer (pure function
  `decimal_odds_to_implied_probabilities`). **Completed** — converts 1X2
  decimal odds to de-vigged baseline probabilities; validates inputs and
  raises `ValueError` for non-numeric or `<= 1.0` odds.
- `tests/test_odds.py` — 5 `unittest` tests for the odds layer (normal market,
  heavy favourite, sum-to-1.0, invalid odds, non-numeric odds). All passing.
- `src/predictor.py` — deterministic predictor/blending math layer (pure
  function `blend_probabilities`). **Completed** — takes a de-vigged baseline
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
  `log_loss`, `compare_prediction_to_baseline`). **Completed** — judges a
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
- `app.py` — minimal Streamlit shell. **Completed.** Imports `init_db`
  (`src/db`), `decimal_odds_to_implied_probabilities` (`src/odds`), and
  `blend_probabilities` (`src/predictor`); calls `init_db()` once at startup
  (no row writes). Sections: Match (home/away/label text inputs, not saved),
  Manual bookmaker odds (three decimal-odds number inputs, defaults
  2.20/3.30/3.20, `min_value=1.01`), and Research factors (exactly 3 fixed rows,
  each with enabled checkbox, target/direction selectboxes, magnitude/weight
  sliders 0.0–1.0, and a note). A "Calculate prediction" button de-vigs the
  odds, builds a factors list from enabled rows only, calls
  `blend_probabilities`, and shows raw implied probs, overround/margin,
  de-vigged baseline, blended prediction (with deltas), an applied-factor table,
  and the predictor explanation. Calculation is wrapped in try/except → `st.error`.
  Uses only `st.metric` / `st.write` / `st.table` / `st.json`; no custom CSS,
  no charts. **Now also persists on demand:** the calculation is stashed in
  `st.session_state`, a "Save prediction to local database" button attaches the
  original decimal odds to the de-vig result and calls `save_prediction_flow`,
  a success message reports the inserted ids, and a "Recent saved predictions"
  table renders `list_recent_predictions()`. Writes happen **only** on the Save
  click — never on rerun or on Calculate.
- `requirements.txt` — **Completed.** Single dependency: `streamlit`. (Standard
  library covers everything else.)
- Public-repo readiness docs — **Completed (this session).** `README.md`
  (rewritten for a future public repo: title, description, "What this is" /
  "What this is not", local setup, status, contribution/security/license
  pointers), `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`,
  `LICENSE_RECOMMENDATION.md` (recommends MIT, mentions Apache-2.0 / GPLv3 —
  decision pending), and `docs/PUBLIC_REPO_READINESS.md` (pre-publish
  checklist). Documentation only — no app, DB, or dependency changes.

## Current database status

**Initialized.** `data/worldcup.db` exists with the five core tables created by
`src/db.py`:

- `teams` — name, fifa_code
- `matches` — home/away teams, kickoff, stage, status, scores
- `signals` — bookmaker decimal odds + implied probabilities per match
- `factors` — research factors (type, direction, magnitude, confidence, note)
- `predictions` — blended home/draw/away probabilities + reasoning JSON

> Note: an earlier plan listed the DB as a future task. It is already present —
> verify with the validation commands below rather than re-creating it.

## Next recommended task

**Result entry + scoring persistence.** Now that predictions are saved, let the
owner record the actual outcome for a saved match and score the prediction
against the bookmaker baseline:

1. add a `record_result(match_id, home_score, away_score)` (or
   home/draw/away outcome) helper to `src/db.py` that updates `matches`
   (`status`, `home_score`, `away_score`) for an existing row,
2. in `app.py`, let the owner pick a saved prediction, enter the actual result,
   and call the existing `src/scoring.py` functions
   (`compare_prediction_to_baseline`) to show whether the research nudged the
   probability in the right direction vs. the raw de-vigged baseline,
3. optionally persist the scores (Brier / log-loss + deltas) — consider whether
   this needs a new column/table and log the decision in `DECISIONS.md`,
4. add `unittest` coverage against a temp DB.

Keep it local-first, standard library + Streamlit only, respect every hard
boundary in `AGENTS.md`, and do not introduce cloud/auth/scraping.

## Validation commands

```bash
python3 src/db.py                       # idempotent: re-creates missing tables
sqlite3 data/worldcup.db ".schema"      # confirm the five tables exist
python3 -m compileall src               # catch syntax errors
python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py  # math-layer tests
streamlit run app.py                    # once app.py exists
```

**Last run (2026-06-09, DB persistence session):**
`python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py tests/test_db.py` →
`Ran 45 tests in 0.040s` / `OK` (all 45 passing — 5 odds + 15 predictor +
12 scoring + 13 db).
`python3 -m compileall src app.py` → compiled, no errors.
`streamlit run app.py` → not run in this environment (Streamlit not installed
here); run locally after `python3 -m pip install -r requirements.txt` to confirm
the Save button and recent-predictions table render.

**Last run (2026-06-09, public-repo readiness docs session):**
Documentation-only change; no tests required, but existing tests were run as a
sanity check.
`python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py` →
`Ran 32 tests in 0.001s` / `OK`.
`python3 -m compileall src app.py` → compiled, no errors. No app, DB, or
dependency changes in this session.

## Known gaps

- The app was **not run interactively** in the build environment (Streamlit
  not installed there); the persistence helpers are verified via `test_db.py`
  + `compileall`, but run `streamlit run app.py` locally to confirm the Save
  button, success message, and recent-predictions table render as expected.
- No result entry yet — saved matches keep their default `status='scheduled'`
  with no scores. This is the next task.
- Scoring math (`src/scoring.py`) exists but is not yet wired into any UI; it
  only becomes usable once result entry exists.
- Factor `weight` is stored inside `factors.note` text, not a dedicated column
  (see `DECISIONS.md`). Reading factors back into the predictor would need to
  parse the note; no reader does this yet.
- No edit/delete of saved predictions yet (out of scope for this task).
- Factors are limited to 3 fixed rows; no dynamic add/remove.
- No AI note → factor parser yet.
- **Actual `LICENSE` file not yet chosen/added.** Public-repo readiness docs are
  in place, but the license decision is pending (see `LICENSE_RECOMMENDATION.md`
  and `docs/PUBLIC_REPO_READINESS.md`). A `LICENSE` file must be added before the
  repo is made public.
