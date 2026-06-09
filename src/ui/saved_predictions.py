"""Streamlit UI components for saved predictions."""

import streamlit as st

from src.db import (
    save_prediction_flow,
    list_recent_predictions,
    list_unscored_predictions,
    score_prediction,
    list_scored_predictions,
)
from src.ui.formatting import _pct


def render_save_prediction(calc: dict) -> None:
    """Render the section to save the current calculation to the database."""
    odds = calc["odds"]
    result = calc["result"]

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


def render_recent_predictions() -> None:
    """Render the table of recent saved predictions."""
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


def render_score_saved_prediction() -> None:
    """Render UI to enter actual result and score a saved prediction."""
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


def render_recent_scored_predictions() -> None:
    """Render the table of recent scored predictions."""
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
