# Project Brief

## Project name

**FIFA World Cup Prediction Tool**

## Scope

**Personal use only.** This is a private research tool for one person. It is not
a product, not a public service, and is never deployed. It runs locally on the
owner's machine.

## What the tool does

- Acts as a **disciplined research notebook** for World Cup matches.
- Records fixtures, bookmaker odds, and the owner's research notes.
- Converts bookmaker odds into a **de-vigged baseline probability** for each
  match outcome.
- Lets the owner add **research factors** (form, injuries, travel, etc.) that
  nudge the baseline.
- Blends the baseline with factors into a final **match probability** using
  transparent, deterministic Python.
- Saves predictions, records actual results, and **scores predictions against
  the bookmaker baseline** so the owner can see whether their research adds
  anything.
- Uses AI to **structure and explain** research notes — not to compute the
  numbers.

## What the tool does not do

- Does not place bets or automate betting in any way.
- Does not connect to the cloud, run on a server, or get deployed.
- Does not have user accounts, auth, or payments.
- Does not scrape protected or paywalled sites.
- Does not claim to "beat the bookmakers."
- Does not let an AI invent or silently generate the final probabilities.

## Stack

- **Python** (standard library preferred)
- **Streamlit** UI — `streamlit run app.py`
- **SQLite** at `data/worldcup.db`

## Core user workflow

1. **Add or import fixtures.**
2. **Enter bookmaker odds manually.**
3. **De-vig odds** into baseline probabilities (remove the bookmaker margin).
4. **Add research factors** (notes structured into directional, weighted signals).
5. **Blend baseline + factors** into final match probabilities.
6. **Save the prediction.**
7. **Enter the result** once the match is played.
8. **Score the prediction vs the baseline** to measure whether research helped.

## Guiding principle

> **The bookmaker baseline is the anchor; user research only nudges it.**

Research factors adjust the de-vigged baseline within reason — they never
replace it. The default belief is the market's belief.
