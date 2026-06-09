# Build Rules

Constraints on **how** this tool is built. These exist to keep it simple,
local-first, honest, and inspectable. See [`AGENTS.md`](../AGENTS.md) for the
operating checklists.

## Architecture & stack

- **Local-first only.** Everything runs on the owner's machine, offline.
- **Use the Python standard library** wherever reasonable before reaching for a
  dependency.
- **SQLite over any external database.** Single file at `data/worldcup.db`.
- **Streamlit over a custom frontend.** No bespoke web stack.
- **No cloud** unless explicitly requested later and logged in `DECISIONS.md`.

## Boundaries

- **No user accounts.**
- **No payments.**
- **No betting automation.** The tool never places or proposes live bets.
- **No scraping protected or paywalled websites.**
- **No fake claims about beating bookmakers.** Framing stays honest: the goal is
  disciplined research, not guaranteed edge.

## AI & prediction integrity

- **No hidden AI-generated stats.** Anything an AI produces must be visible.
- **AI outputs must be reviewed by the human before being saved.**
- **Prediction math must be transparent and deterministic.** Same inputs →
  same outputs, every time. No randomness, no model black boxes in the number
  path.
- **AI structures research notes; deterministic Python calculates probabilities.**

## Workflow discipline

- **Keep each change small** — atomic and reversible.
- **Prefer pure functions** for odds math (de-vigging), prediction (blending),
  and scoring logic. Pure functions are testable and auditable.
- **Document every new assumption** — in your handoff, and in `DECISIONS.md` if
  it is structural.
