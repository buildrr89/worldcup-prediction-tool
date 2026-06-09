# FIFA World Cup Prediction Tool

A local-first FIFA World Cup prediction research tool that combines bookmaker
baseline probabilities, manual research factors, deterministic probability
blending, and post-match scoring. Python + Streamlit + SQLite. Runs offline on
your own machine.

## What this is

- A **disciplined research notebook** for World Cup matches.
- A tool that converts manually entered bookmaker odds into a **de-vigged
  baseline probability** (the bookmaker margin removed).
- A way to add **research factors** (form, injuries, travel, etc.) that nudge
  that baseline within reason.
- A **deterministic blending layer** — the same inputs always produce the same
  outputs. Pure Python, no randomness, no black boxes in the number path.
- A **post-match scoring layer** (Brier score and log loss) that measures
  whether your research nudged the probability in the right direction vs. the
  raw bookmaker baseline.
- Built around one principle: **the bookmaker baseline is the anchor; research
  only nudges it.**

AI may be used to *structure and explain* research notes — it never computes or
invents the final numbers.

## What this is not

- **Not betting automation.** It never places, proposes, or executes bets.
- **Not financial advice.** Nothing here is a recommendation to wager money.
- **Not guaranteed predictions.** Probabilities are estimates, not outcomes.
- **Not a bookmaker-beating machine.** The goal is disciplined research, not a
  guaranteed edge.
- **Not a public SaaS (yet).** It is a personal, local-first research tool.

## Local setup

Requires Python 3. From the project root:

```bash
# 1. Install the single dependency (Streamlit)
python3 -m pip install -r requirements.txt

# 2. Initialize / verify the local SQLite database
python3 src/db.py

# 3. Run the math-layer tests
python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py

# 4. Launch the app
streamlit run app.py
```

## Current status

The core math layers (odds de-vig, deterministic predictor/blending, scoring)
are built and tested. A Streamlit shell on top lets you enter odds and factors,
see the baseline and blended probabilities, and explicitly save the full flow
(match, signal, factors, prediction) to the local SQLite database. The next
planned task is result entry + scoring persistence. See
[docs/STATUS.md](docs/STATUS.md) for the authoritative, up-to-date picture
(current stage, next task, known gaps).

## Start here

- **[AGENTS.md](AGENTS.md)** — primary instructions for any coding agent.
- **[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)** — what this tool is and does.
- **[docs/STATUS.md](docs/STATUS.md)** — current stage, next task, known gaps.

Also useful: [docs/BUILD_RULES.md](docs/BUILD_RULES.md),
[docs/DECISIONS.md](docs/DECISIONS.md),
[docs/HANDOFF_TEMPLATE.md](docs/HANDOFF_TEMPLATE.md).

## Contributing

Contributions are welcome — please read [CONTRIBUTING.md](CONTRIBUTING.md)
first. It explains the local-first scope, the "one focused change at a time"
rule, and the checklist to run before opening a PR.

## Security

Please do not commit secrets, API keys, tokens, or local database files. See
[SECURITY.md](SECURITY.md) for how to report a problem and what must never be
committed.

## License

**No license has been chosen yet.** Until one is added, default copyright rules
apply and others may not freely reuse, modify, or distribute the code. See
[LICENSE_RECOMMENDATION.md](LICENSE_RECOMMENDATION.md) for the recommendation
and the pending decision.
