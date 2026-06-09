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
    list_scored_predictions,
    list_unscored_predictions,
    save_prediction_flow,
    score_prediction,
    save_historical_import,
    list_historical_import_batches,
    list_historical_matches,
    get_historical_batch_summary,
    list_historical_batch_summaries,
    compare_historical_batches,
)
from src.odds import decimal_odds_to_implied_probabilities
from src.predictor import blend_probabilities
from src.importers.football_data_csv import (
    load_csv_file,
    summarise_historical_matches,
    backtest_baseline,
)

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

# --- Score saved prediction ------------------------------------------------
st.header("Score saved prediction")
st.caption(
    "Record the actual result for a saved prediction and score it against "
    "the bookmaker baseline."
)

unscored = list_unscored_predictions()
if not unscored:
    st.write("No unscored predictions available.")
else:
    def format_unscored(pred):
        return f"ID #{pred['prediction_id']}: {pred['home_team']} vs {pred['away_team']} ({pred['stage'] or 'N/A'})"

    selected_pred = st.selectbox(
        "Select saved prediction",
        options=unscored,
        format_func=format_unscored,
        key="unscored_prediction_selectbox",
    )

    actual_result = st.selectbox(
        "Actual result",
        options=("home", "draw", "away"),
        key="actual_result_selectbox",
    )

    if st.button("Score selected prediction", key="score_prediction_button"):
        try:
            score_res = score_prediction(selected_pred["prediction_id"], actual_result)
            st.success(
                f"Successfully scored prediction #{selected_pred['prediction_id']}!"
            )

            # Display comparison using st.table
            comparison_data = [
                {
                    "Metric": "Brier Score (lower is better)",
                    "Prediction": f"{score_res['prediction_brier']:.4f}",
                    "Baseline": f"{score_res['baseline_brier']:.4f}",
                    "Delta": f"{score_res['brier_delta']:+.4f}",
                    "Improved?": "✅ Yes" if score_res["prediction_improved_brier"] else "❌ No",
                },
                {
                    "Metric": "Log Loss (lower is better)",
                    "Prediction": f"{score_res['prediction_log_loss']:.4f}",
                    "Baseline": f"{score_res['baseline_log_loss']:.4f}",
                    "Delta": f"{score_res['log_loss_delta']:+.4f}",
                    "Improved?": "✅ Yes" if score_res["prediction_improved_log_loss"] else "❌ No",
                },
            ]
            st.table(comparison_data)
        except Exception as error:
            st.error(f"Scoring failed: {error}")

# --- Recent scored predictions ---------------------------------------------
st.header("Recent scored predictions")
st.caption("The most recent scored predictions in the local database.")
scored = list_scored_predictions()
if scored:
    st.table(
        [
            {
                "ID": r["prediction_id"],
                "Match": f"{r['home_team']} vs {r['away_team']}",
                "Actual Result": r["actual_result"],
                "Pred Brier": f"{r['prediction_brier']:.4f}",
                "Base Brier": f"{r['baseline_brier']:.4f}",
                "Brier Delta": f"{r['brier_delta']:+.4f}",
                "Pred LogLoss": f"{r['prediction_log_loss']:.4f}",
                "Base LogLoss": f"{r['baseline_log_loss']:.4f}",
                "LogLoss Delta": f"{r['log_loss_delta']:+.4f}",
                "Scored at": r["scored_at"],
            }
            for r in scored
        ]
    )
else:
    st.write("No predictions scored yet.")


# --- Historical CSV backtest preview ---------------------------------------
st.header("Historical CSV backtest preview")
st.caption(
    "Upload a local Football-Data.co.uk-style CSV to preview matches, summary stats, "
    "and baseline backtest results. No database writes happen here."
)

# 1. file uploader
uploaded_file = st.file_uploader(
    "Upload historical CSV file",
    type=["csv"],
    key="historical_csv_uploader"
)

# 2. select odds prefix
odds_prefix = st.text_input(
    "Odds prefix",
    value="B365",
    help="The column prefix for bookmaker odds. Examples: B365, PS.",
    key="historical_odds_prefix"
)

if uploaded_file is not None:
    try:
        # Track file to clear saved status if a new file is uploaded
        current_file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_uploaded_file_key") != current_file_key:
            st.session_state["last_uploaded_file_key"] = current_file_key
            st.session_state.pop("last_historical_save", None)
            st.session_state.pop("historical_save_error", None)

        # 3. parse matches
        matches = load_csv_file(uploaded_file, odds_prefix=odds_prefix)
        
        # 6. Show clear messages: no DB writes happen yet, preview only, skipped rows
        st.info(
            "ℹ️ **Preview mode active.** No database writes will occur. "
            f"Unsupported or missing odds rows using prefix `{odds_prefix}` are automatically skipped."
        )
        
        if not matches:
            st.warning(f"No valid matches found with odds prefix `{odds_prefix}` in the uploaded file.")
        else:
            # summarise and backtest
            summary = summarise_historical_matches(matches)
            backtest = backtest_baseline(matches)
            
            # 4. Show summary and backtest metrics
            st.subheader("Backtest summary")
            
            col_m1 = st.columns(4)
            col_m1[0].metric("Valid matches", summary["match_count"])
            col_m1[1].metric("Home wins", summary["home_wins"])
            col_m1[2].metric("Draws", summary["draws"])
            col_m1[3].metric("Away wins", summary["away_wins"])
            
            col_m2 = st.columns(3)
            col_m2[0].metric("Avg bookmaker margin", _pct(summary["average_margin"]))
            col_m2[1].metric("Avg baseline Brier", f"{backtest['average_brier']:.4f}")
            col_m2[2].metric("Avg baseline Log Loss", f"{backtest['average_log_loss']:.4f}")
            
            # 5. Show a simple preview table of the first 10 parsed matches
            st.subheader("First 10 matches preview")
            preview_rows = []
            for m in matches[:10]:
                preview_rows.append({
                    "date": m["date"],
                    "home_team": m["home_team"],
                    "away_team": m["away_team"],
                    "actual_result": m["actual_result"],
                    "home_decimal_odds": f"{m['home_decimal_odds']:.2f}",
                    "draw_decimal_odds": f"{m['draw_decimal_odds']:.2f}",
                    "away_decimal_odds": f"{m['away_decimal_odds']:.2f}",
                    "baseline_home": _pct(m["baseline"]["home"]),
                    "baseline_draw": _pct(m["baseline"]["draw"]),
                    "baseline_away": _pct(m["baseline"]["away"]),
                    "margin": _pct(m["margin"])
                })
            st.table(preview_rows)

            # DB persistence after preview approval
            st.subheader("Persist parsed matches")
            st.caption(
                "Click the button below to persist the parsed matches and backtest baseline scores "
                "to the local SQLite database."
            )
            if st.button("Save parsed historical import to local database", key="save_historical_import_button"):
                try:
                    file_name = uploaded_file.name if hasattr(uploaded_file, "name") else None
                    save_res = save_historical_import(matches, odds_prefix, file_name)
                    st.session_state["last_historical_save"] = save_res
                    st.session_state.pop("historical_save_error", None)
                except Exception as error:
                    st.session_state["historical_save_error"] = str(error)
                    st.session_state.pop("last_historical_save", None)

            if "historical_save_error" in st.session_state:
                st.error(f"Save failed: {st.session_state['historical_save_error']}")

            if "last_historical_save" in st.session_state:
                save_res = st.session_state["last_historical_save"]
                st.success(
                    f"Successfully saved historical import batch #{save_res['batch_id']}!\n"
                    f"Match count: {save_res['match_count']} matches.\n"
                    f"Average baseline Brier: {save_res['average_brier']:.4f}\n"
                    f"Average baseline Log Loss: {save_res['average_log_loss']:.4f}"
                )
                st.warning("⚠️ This stores parsed match records only, not the raw uploaded CSV file.")
            
    except Exception as error:
        # 7. Handle errors with st.error(str(error))
        st.error(str(error))

# --- Recent historical import batches --------------------------------------
st.header("Recent historical import batches")
st.caption("Saved batches from historical imports.")
recent_batches = list_historical_import_batches(limit=10)
if recent_batches:
    st.table(
        [
            {
                "Batch ID": b["id"],
                "Odds Prefix": b["odds_prefix"],
                "File Name": b["file_name"] or "N/A",
                "Matches": b["match_count"],
                "Avg Margin": _pct(b["average_margin"]),
                "Avg Brier": f"{b['average_brier']:.4f}",
                "Avg LogLoss": f"{b['average_log_loss']:.4f}",
                "Imported at": b["created_at"],
            }
            for b in recent_batches
        ]
    )
    
    # Optionally show first few rows for the most recent batch using list_historical_matches
    latest_batch_id = recent_batches[0]["id"]
    st.markdown(f"**First 5 matches from latest batch #{latest_batch_id}**")
    recent_matches = list_historical_matches(latest_batch_id, limit=5)
    if recent_matches:
        st.table(
            [
                {
                    "Date": m["match_date"],
                    "Home Team": m["home_team"],
                    "Away Team": m["away_team"],
                    "Result": m["actual_result"],
                    "Home Odds": f"{m['home_decimal_odds']:.2f}",
                    "Draw Odds": f"{m['draw_decimal_odds']:.2f}",
                    "Away Odds": f"{m['away_decimal_odds']:.2f}",
                    "Margin": _pct(m["margin"]),
                }
                for m in recent_matches
            ]
        )
else:
    st.write("No historical import batches saved yet.")

# --- Historical backtest dashboard -----------------------------------------
st.header("Historical backtest dashboard")
st.caption(
    "Compare metrics and distributions across saved historical CSV import batches. "
    "This dashboard is read-only."
)

comparison = compare_historical_batches()

if comparison["batch_count"] == 0:
    st.info("No saved historical imports yet. Upload and save a historical CSV import first.")
else:
    st.subheader("Aggregate metrics")
    tot_batches = comparison["batch_count"]
    tot_matches = sum(b["match_count"] for b in comparison["batches"])
    
    col_dash1 = st.columns(4)
    col_dash1[0].metric("Total saved batches", tot_batches)
    col_dash1[1].metric("Total saved matches", tot_matches)
    
    if comparison["best_brier_batch"]:
        best_brier = comparison["best_brier_batch"]["average_brier"]
        col_dash1[2].metric("Best avg Brier score", f"{best_brier:.4f}")
    if comparison["best_log_loss_batch"]:
        best_ll = comparison["best_log_loss_batch"]["average_log_loss"]
        col_dash1[3].metric("Best avg Log Loss", f"{best_ll:.4f}")

    st.subheader("Comparison of saved batches")
    st.table(
        [
            {
                "Batch ID": b["id"],
                "Odds Prefix": b["odds_prefix"],
                "File Name": b["file_name"] or "N/A",
                "Matches": b["match_count"],
                "Avg Margin": _pct(b["average_margin"]),
                "Avg Brier": f"{b['average_brier']:.4f}",
                "Avg LogLoss": f"{b['average_log_loss']:.4f}",
            }
            for b in comparison["batches"]
        ]
    )

    st.subheader("Brier score & Log Loss across batches")
    chart_data = []
    for b in reversed(comparison["batches"]):
        chart_data.append({
            "Batch": f"Batch #{b['id']}",
            "Brier Score": b["average_brier"],
            "Log Loss": b["average_log_loss"]
        })
    st.bar_chart(chart_data, x="Batch", y=["Brier Score", "Log Loss"])

    st.subheader("Result distribution")
    st.table(
        [
            {
                "Batch ID": b["id"],
                "Home Wins": b["home_wins"],
                "Draws": b["draws"],
                "Away Wins": b["away_wins"],
                "Home Win %": _pct(b["home_wins"] / b["match_count"]) if b["match_count"] > 0 else "0.0%",
                "Draw %": _pct(b["draws"] / b["match_count"]) if b["match_count"] > 0 else "0.0%",
                "Away Win %": _pct(b["away_wins"] / b["match_count"]) if b["match_count"] > 0 else "0.0%",
            }
            for b in comparison["batches"]
        ]
    )
