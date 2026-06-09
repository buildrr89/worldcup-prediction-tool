"""Streamlit UI components for the historical backtest comparison dashboard."""

import streamlit as st

from src.db import compare_historical_batches
from src.ui.formatting import _pct


def render_historical_dashboard() -> None:
    """Render the comparison dashboard metrics, comparison tables, charts, and distribution tables."""
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
