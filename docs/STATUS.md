# Status

> Single source of truth for "where we are." Update this after any meaningful
> work — it is how every tool (Claude Code, Codex, Antigravity, …) stays in sync.

**Last updated:** 2026-06-10

## Current stage

Core math layer, manual SQLite persistence, post-match prediction scoring/persistence, Football-Data.co.uk CSV importing foundation, Streamlit historical CSV upload/import preview, DB persistence for selected historical CSV imports after preview approval, a baseline backtest dashboard comparing saved historical CSV import batches, a legally safe synthetic sample CSV quick-start demo flow, and public collaboration configuration (GitHub templates and contributor labels) are complete. Standard library parsing translates uploaded historical match and betting odds CSVs in-memory to baseline probabilities, calculates summary stats, and evaluates baseline backtests, offering the user an option to persist the structured matches to the local SQLite database.

## GitHub connection status

- **Status:** Connected to GitHub
- **Repository URL:** [worldcup-prediction-tool](https://github.com/buildrr89/worldcup-prediction-tool)
- **Visibility:** Public
- **Latest public-release commit hash:** `4f9984d`
- **Branch:** `main`
- **License:** MIT
- **Public release:** Live

## Completed files

- Governance docs: `AGENTS.md`, `CLAUDE.md`, `README.md`,
  `docs/PROJECT_BRIEF.md`, `docs/BUILD_RULES.md`, `docs/STATUS.md`,
  `docs/DECISIONS.md`, `docs/HANDOFF_TEMPLATE.md`.
- `src/db.py` — SQLite foundation (connection helper + `init_db()`) plus
  manual persistence helpers: `create_match`, `create_signal`,
  `create_factor`, `create_prediction`, `save_prediction_flow` (single
  transaction, no partial saves), `list_recent_predictions`,
  `get_prediction_for_scoring`, `score_prediction`,
  `list_unscored_predictions`, `list_scored_predictions`,
  `create_historical_import_batch`, `create_historical_match`,
  `save_historical_import`, `list_historical_import_batches`, `list_historical_matches`,
  `get_historical_batch_summary`, `list_historical_batch_summaries`, and `compare_historical_batches`.
- `tests/test_db.py` — 37 `unittest` tests for the persistence, migration, historical CSV import, and batch comparison layers, each
  against a `tempfile.TemporaryDirectory` DB. All passing.
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
- `app.py` — Streamlit shell. Completed. Supports manual match prediction, post-match prediction scoring, historical CSV preview and backtesting, persisting approved historical CSV imports to SQLite with automatic batch listing, a baseline backtest dashboard comparing saved import batches, and a Quick-start demo section for downloading the synthetic sample CSV.
- `requirements.txt` — Completed. Single dependency: `streamlit`. (Standard
  library covers everything else.)
- Public-repo readiness docs & templates — Completed. `README.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `LICENSE_RECOMMENDATION.md`,
  `docs/PUBLIC_REPO_READINESS.md` (checklist), `.github/ISSUE_TEMPLATE/` (bug_report.yml, feature_request.yml, data_source_request.yml, research_note_parser.yml, config.yml), `.github/PULL_REQUEST_TEMPLATE.md`, and `.github/labels.yml`.
- `src/importers/__init__.py` and `src/importers/football_data_csv.py` — Football-Data.co.uk CSV importer/backtesting foundation. Completed — parses historical results/odds from filesystem path or file-like/bytes objects, calculates de-vigged baseline probabilities, computes summary statistics (wins, margins), and performs baseline backtesting (Brier score and log loss).
- `tests/test_football_data_csv.py` — 18 `unittest` tests for the CSV importer/backtester (result mapping, float parsing, match mapping, load CSV with error line numbers, load CSV file from String/Bytes streams, invalid row skipping, error row-attribution, summarisation, backtest calculations, alternative odds prefixes, and synthetic sample CSV compatibility). All passing.
- `sample_data/football_data_sample.csv` — Completed. Legally safe, synthetic CSV containing 10 fictional match rows to test import/backtest flow.

## Current database status

**Initialized.** `data/worldcup.db` exists with the five core tables created by
`src/db.py`:

- `teams` — name, fifa_code
- `matches` — home/away teams, kickoff, stage, status, scores
- `signals` — bookmaker decimal odds + implied probabilities per match
- `factors` — research factors (type, direction, magnitude, confidence, note)
- `predictions` — blended home/draw/away probabilities + reasoning JSON + actual result outcome + Brier & log-loss evaluation scores
- `historical_import_batches` — batches of historical imports
- `historical_matches` — historical match records associated with batches

## Next recommended task

**Create first public good-first-issue backlog for sample data, importer UX, and documentation polish.**

## Validation commands

```bash
python3 src/db.py                       # idempotent: re-creates missing tables and applies schema updates
sqlite3 data/worldcup.db ".schema"      # confirm the tables and columns exist
python3 -m compileall src app.py        # catch syntax errors
python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py tests/test_db.py tests/test_football_data_csv.py  # run all 71 tests
streamlit run app.py                    # launch the app
```

**Last run (2026-06-10, GitHub templates & labels session):**
`python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py tests/test_db.py tests/test_football_data_csv.py` →
`Ran 87 tests in 0.232s` / `OK` (all 87 passing).
`python3 -m compileall src app.py` → compiled successfully.

## Known gaps

- The app was **not run interactively** in the build environment (Streamlit
  not installed there); the widgets are verified via `compileall` and database functions,
  but run `streamlit run app.py` locally to confirm UI flow behaves correctly.
- Factor `weight` is stored inside `factors.note` text, not a dedicated column.
- No edit/delete of saved predictions yet.
- Factors are limited to 3 fixed rows.
- No AI note → factor parser yet.
