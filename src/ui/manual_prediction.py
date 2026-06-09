"""Streamlit UI components for manual match predictions and factor blending."""

import streamlit as st

from src.odds import decimal_odds_to_implied_probabilities
from src.predictor import blend_probabilities
from src.ui.formatting import _pct
from src.ui.saved_predictions import render_save_prediction

FACTOR_ROWS = 3


def render_manual_prediction() -> None:
    """Render the manual prediction input form, calculate prediction logic, and results."""
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
    # Save button.
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

        # Call the save rendering from saved_predictions module
        render_save_prediction(calc)
