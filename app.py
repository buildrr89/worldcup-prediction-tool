"""Minimal Streamlit shell for the FIFA World Cup prediction research tool.

Local-first, personal use only. Wires the existing deterministic math layers
(`src/odds.py`, `src/predictor.py`) together behind a simple Streamlit UI. This
shell lets the owner enter bookmaker odds and research factors by hand, then see
the de-vigged baseline and the blended prediction.

`init_db()` is called once at startup so the local SQLite foundation exists.
Nothing is written on a Streamlit rerun: rows are only persisted when the owner
explicitly clicks "Save prediction to local database" after a calculation.

Run locally with:

    streamlit run app.py
"""

import streamlit as st

from src.db import (
    init_db,
    list_recent_predictions,
    save_prediction_flow,
)
from src.odds import decimal_odds_to_implied_probabilities
from src.predictor import blend_probabilities

# Ensure the local SQLite foundation exists. This does not write any rows; it
# only creates the tables if they are missing. Idempotent and offline.
init_db()

# How many manual research-factor rows the shell shows for now. Kept fixed and
# small — no dynamic add/remove yet.
FACTOR_ROWS = 3


def _pct(value: float) -> str:
    """Format a probability (0.0–1.0) as a readable percentage string."""
    return f"{value * 100:.1f}%"


st.title("FIFA World Cup Prediction Tool")

st.write(
    "A **personal-use, local research tool** — not a product, not a betting bot. "
    "The **bookmaker baseline is the anchor**: bookmaker odds are de-vigged into "
    "baseline probabilities, and your **research factors only nudge that "
    "baseline** within a bounded range. **No prediction is guaranteed** — this is "
    "disciplined research, not a promise of edge."
)

# --- Match -----------------------------------------------------------------
st.header("Match")
st.caption("Describe the fixture. This does not save anything yet.")
home_team = st.text_input("Home team", value="")
away_team = st.text_input("Away team", value="")
match_label = st.text_input("Match label / stage (optional)", value="")

# --- Manual bookmaker odds -------------------------------------------------
st.header("Manual bookmaker odds")
st.caption("Decimal odds. Each must be greater than 1.0.")
odds_cols = st.columns(3)
with odds_cols[0]:
    home_odds = st.number_input(
        "Home decimal odds", min_value=1.01, value=2.20, step=0.01, format="%.2f"
    )
with odds_cols[1]:
    draw_odds = st.number_input(
        "Draw decimal odds", min_value=1.01, value=3.30, step=0.01, format="%.2f"
    )
with odds_cols[2]:
    away_odds = st.number_input(
        "Away decimal odds", min_value=1.01, value=3.20, step=0.01, format="%.2f"
    )

# --- Research factors ------------------------------------------------------
st.header("Research factors")
st.caption(
    "Up to three manual factors for now. Only enabled rows are applied. Each "
    "factor nudges one outcome (home/draw/away) by magnitude × weight, capped."
)

factor_inputs = []
for i in range(FACTOR_ROWS):
    st.markdown(f"**Factor {i + 1}**")
    enabled = st.checkbox("Enabled", value=False, key=f"factor_{i}_enabled")
    row = st.columns(4)
    with row[0]:
        target = st.selectbox(
            "Target", ("home", "draw", "away"), key=f"factor_{i}_target"
        )
    with row[1]:
        direction = st.selectbox(
            "Direction", ("positive", "negative"), key=f"factor_{i}_direction"
        )
    with row[2]:
        magnitude = st.slider(
            "Magnitude", 0.0, 1.0, value=0.0, step=0.01, key=f"factor_{i}_magnitude"
        )
    with row[3]:
        weight = st.slider(
            "Weight", 0.0, 1.0, value=0.0, step=0.01, key=f"factor_{i}_weight"
        )
    note = st.text_input("Note", value="", key=f"factor_{i}_note")

    factor_inputs.append(
        {
            "enabled": enabled,
            "target": target,
            "direction": direction,
            "magnitude": magnitude,
            "weight": weight,
            "note": note,
        }
    )

# --- Calculate -------------------------------------------------------------
if st.button("Calculate prediction"):
    try:
        odds = decimal_odds_to_implied_probabilities(home_odds, draw_odds, away_odds)

        # Build the factors list from enabled rows only, in the shape
        # blend_probabilities expects.
        factors = [
            {
                "target": f["target"],
                "direction": f["direction"],
                "magnitude": f["magnitude"],
                "weight": f["weight"],
                "note": f["note"],
            }
            for f in factor_inputs
            if f["enabled"]
        ]

        baseline = {"home": odds["home"], "draw": odds["draw"], "away": odds["away"]}
        result = blend_probabilities(baseline, factors)

        # Stash the full calculation in session state so the Save button — which
        # triggers a fresh rerun where the Calculate button reads False — can
        # persist it without recomputing. Nothing is written to the DB here.
        st.session_state["last_calculation"] = {
            "match": {
                "home_team": home_team,
                "away_team": away_team,
                "stage": match_label or None,
            },
            "odds": odds,
            "home_odds": home_odds,
            "draw_odds": draw_odds,
            "away_odds": away_odds,
            "factors": factors,
            "result": result,
        }
        # A new calculation supersedes any earlier save confirmation.
        st.session_state.pop("last_save", None)
    except Exception as error:  # noqa: BLE001 — surface any input error, never crash.
        st.error(str(error))
        st.session_state.pop("last_calculation", None)

# --- Results + save --------------------------------------------------------
# Render from session state so the display survives the rerun caused by the
# Save button below.
if "last_calculation" in st.session_state:
    calc = st.session_state["last_calculation"]
    odds = calc["odds"]
    result = calc["result"]

    with st.container():
        st.subheader("Raw implied probabilities")
        st.caption("Straight from the odds (1 / odds) — still include the margin.")
        raw_cols = st.columns(3)
        raw_cols[0].metric("Home", _pct(odds["raw_home"]))
        raw_cols[1].metric("Draw", _pct(odds["raw_draw"]))
        raw_cols[2].metric("Away", _pct(odds["raw_away"]))

        st.subheader("Bookmaker margin")
        margin_cols = st.columns(2)
        margin_cols[0].metric("Overround", _pct(odds["overround"]))
        margin_cols[1].metric("Margin (vig)", _pct(odds["margin"]))

        st.subheader("De-vigged baseline probabilities")
        st.caption("The anchor — margin removed, sums to ~100%.")
        base_cols = st.columns(3)
        base_cols[0].metric("Home", _pct(odds["home"]))
        base_cols[1].metric("Draw", _pct(odds["draw"]))
        base_cols[2].metric("Away", _pct(odds["away"]))

        st.subheader("Blended prediction probabilities")
        st.caption("Baseline nudged by enabled research factors.")
        pred_cols = st.columns(3)
        pred_cols[0].metric(
            "Home", _pct(result["home"]),
            delta=_pct(result["home"] - odds["home"]),
        )
        pred_cols[1].metric(
            "Draw", _pct(result["draw"]),
            delta=_pct(result["draw"] - odds["draw"]),
        )
        pred_cols[2].metric(
            "Away", _pct(result["away"]),
            delta=_pct(result["away"] - odds["away"]),
        )

        st.subheader("Applied factors")
        if result["applied_factors"]:
            st.table(
                [
                    {
                        "Target": f["target"],
                        "Direction": f["direction"],
                        "Magnitude": f["magnitude"],
                        "Weight": f["weight"],
                        "Shift": f"{f['shift'] * 100:+.2f}%",
                        "Note": f["note"] or "",
                    }
                    for f in result["applied_factors"]
                ]
            )
        else:
            st.write("No factors enabled — prediction equals the baseline.")

        st.subheader("Explanation")
        st.write(result["explanation"])

        with st.expander("Raw blended result (debug)"):
            st.json(result)

    # --- Save to local SQLite ----------------------------------------------
    st.subheader("Save")
    st.caption(
        "Nothing is saved automatically. Click below to persist this match, its "
        "odds signal, the enabled factors, and the prediction to the local "
        "database."
    )
    if st.button("Save prediction to local database"):
        match = calc["match"]
        if not (match["home_team"].strip() and match["away_team"].strip()):
            st.error("Enter both a home team and an away team before saving.")
        else:
            try:
                # Attach the original decimal odds so the signal row keeps them
                # (the de-vig output alone does not preserve the entered odds).
                odds_to_save = dict(odds)
                odds_to_save["home_decimal_odds"] = calc["home_odds"]
                odds_to_save["draw_decimal_odds"] = calc["draw_odds"]
                odds_to_save["away_decimal_odds"] = calc["away_odds"]

                ids = save_prediction_flow(
                    match, odds_to_save, calc["factors"], result
                )
                st.session_state["last_save"] = ids
            except Exception as error:  # noqa: BLE001 — surface DB errors, never crash.
                st.error(f"Save failed: {error}")

    if "last_save" in st.session_state:
        ids = st.session_state["last_save"]
        st.success(
            f"Saved — match #{ids['match_id']}, signal #{ids['signal_id']}, "
            f"factors {ids['factor_ids']}, prediction #{ids['prediction_id']}."
        )

# --- Recent saved predictions ----------------------------------------------
st.header("Recent saved predictions")
st.caption("The most recent predictions persisted to the local database.")
recent = list_recent_predictions()
if recent:
    st.table(
        [
            {
                "ID": r["prediction_id"],
                "Match": f"{r['home_team']} vs {r['away_team']}",
                "Stage": r["stage"] or "",
                "Home": _pct(r["home_probability"]),
                "Draw": _pct(r["draw_probability"]),
                "Away": _pct(r["away_probability"]),
                "Saved at": r["created_at"],
            }
            for r in recent
        ]
    )
else:
    st.write("No predictions saved yet.")
