"""Streamlit UI components for the manual prediction performance and calibration dashboard."""

import streamlit as st

from src.db import (
    get_prediction_performance_summary,
    list_prediction_performance_rows,
    build_prediction_calibration_bins,
)
from src.ui.formatting import _pct


def render_prediction_performance_dashboard() -> None:
    """Render the dashboard evaluating saved manual predictions against the bookmaker baseline."""
    st.header("Manual prediction performance")
    st.caption(
        "Evaluate whether your manual research-factor predictions improve on the raw "
        "bookmaker baseline over time. Lower Brier score and log loss are better; "
        "negative delta means manual prediction improved on the baseline. "
        "This section only uses saved predictions that have been scored with final results. "
        "This dashboard is read-only."
    )

    summary = get_prediction_performance_summary()

    if summary["scored_count"] == 0:
        st.info("No scored manual predictions yet. Save predictions and score results first.")
        return

    # 1. Summary Metrics
    st.subheader("Performance summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Scored predictions", summary["scored_count"])

    # Average Brier score comparison
    col2.metric(
        label="Avg manual Brier",
        value=f"{summary['average_prediction_brier']:.4f}",
        delta=f"{summary['average_brier_delta']:.4f}",
        delta_color="inverse",
    )

    # Average Log Loss comparison
    col3.metric(
        label="Avg manual Log Loss",
        value=f"{summary['average_prediction_log_loss']:.4f}",
        delta=f"{summary['average_log_loss_delta']:.4f}",
        delta_color="inverse",
    )

    # 2. Verdict Banner
    b_delta = summary["average_brier_delta"]
    ll_delta = summary["average_log_loss_delta"]

    st.markdown("### Verdict")
    if b_delta < 0 and ll_delta < 0:
        st.success("Manual research is currently improving on the bookmaker baseline.")
    elif (b_delta < 0 and ll_delta >= 0) or (b_delta >= 0 and ll_delta < 0):
        st.warning("Manual research is mixed so far.")
    else:
        st.error("Manual research is not yet improving on the bookmaker baseline.")

    # 3. Bar Chart comparing Manual vs Baseline
    st.markdown("### Average scores comparison")
    chart_data = [
        {
            "Metric": "Brier Score",
            "Manual": summary["average_prediction_brier"],
            "Baseline": summary["average_baseline_brier"],
        },
        {
            "Metric": "Log Loss",
            "Manual": summary["average_prediction_log_loss"],
            "Baseline": summary["average_baseline_log_loss"],
        },
    ]
    st.bar_chart(chart_data, x="Metric", y=["Manual", "Baseline"])

    # 4. Improvement counts
    st.markdown("### Improvement distribution")
    st.table(
        [
            {
                "Metric": "Brier Score",
                "Improved (Delta < 0)": summary["brier_improved_count"],
                "Tied (Delta = 0)": summary["brier_tied_count"],
                "Worsened (Delta > 0)": summary["brier_worsened_count"],
            },
            {
                "Metric": "Log Loss",
                "Improved (Delta < 0)": summary["log_loss_improved_count"],
                "Tied (Delta = 0)": summary["log_loss_tied_count"],
                "Worsened (Delta > 0)": summary["log_loss_worsened_count"],
            },
        ]
    )

    # 5. Calibration/Reliability Bins
    st.markdown("### Probability calibration")
    st.write(
        "Calibration groups predicted probabilities of outcomes (home, draw, away) "
        "into bins, and compares the average predicted probability in each bin against "
        "the actual observed outcome hit rate (one-vs-rest). A perfectly calibrated "
        "forecaster has hit rates that match the predicted probabilities."
    )

    bin_size = st.slider(
        "Bin size for calibration",
        min_value=0.05,
        max_value=0.50,
        value=0.10,
        step=0.05,
        key="calibration_bin_size_slider",
    )

    bins = build_prediction_calibration_bins(bin_size)

    if bins:
        st.table(
            [
                {
                    "Bin (Lower Bound)": f"{b['bin']:.2f}",
                    "Bin Range": f"[{b['bin']:.2f}, {min(1.0, b['bin'] + bin_size):.2f})",
                    "Sample Size": b["count"],
                    "Avg Predicted Prob": _pct(b["average_predicted_probability"]),
                    "Observed Hit Rate": _pct(b["actual_hit_rate"]),
                }
                for b in bins
            ]
        )

        # Bar chart for calibration
        cal_chart_data = [
            {
                "Bin": f"{b['bin']:.2f}",
                "Predicted Prob": b["average_predicted_probability"],
                "Observed Hit Rate": b["actual_hit_rate"],
            }
            for b in bins
        ]
        st.bar_chart(cal_chart_data, x="Bin", y=["Predicted Prob", "Observed Hit Rate"])
    else:
        st.info("No calibration bins built.")

    # 6. Scored predictions list
    st.markdown("### Recent scored predictions")
    rows = list_prediction_performance_rows(50)
    if rows:
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
                for r in rows
            ]
        )
    else:
        st.write("No scored predictions found.")
