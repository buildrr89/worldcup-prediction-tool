"""Minimal Streamlit shell for the FIFA World Cup prediction research tool.

Local-first, personal use only. Wires the modular UI components together.
Streamlit Session State persists values between reruns, which preserves
user input and calculations.

Run locally with:

    streamlit run app.py
"""

import streamlit as st

from src.db import init_db
from src.ui.demo import render_quick_start_demo
from src.ui.historical_csv import (
    render_historical_csv_preview,
    render_recent_historical_batches,
)
from src.ui.historical_dashboard import render_historical_dashboard
from src.ui.manual_prediction import render_manual_prediction
from src.ui.saved_predictions import (
    render_recent_predictions,
    render_recent_scored_predictions,
    render_score_saved_prediction,
)

# Ensure the local SQLite foundation exists. This does not write any rows; it
# only creates the tables if they are missing. Idempotent and offline.
init_db()

# Page title and introductory disclaimer
st.title("FIFA World Cup Prediction Tool")
st.write(
    "A **personal-use, local research tool** — not a product, not a betting bot. "
    "The **bookmaker baseline is the anchor**: bookmaker odds are de-vigged into "
    "baseline probabilities, and your **research factors only nudge that "
    "baseline** within a bounded range. **No prediction is guaranteed** — this is "
    "disciplined research, not a promise of edge."
)

# Render the manual prediction form, results, and save workflow
render_manual_prediction()

# Render lists and workflows for saved predictions
render_recent_predictions()
render_score_saved_prediction()
render_recent_scored_predictions()

# Render historical CSV backtest preview and uploader
st.header("Historical CSV backtest preview")
st.caption(
    "Upload a local Football-Data.co.uk-style CSV to preview matches, summary stats, "
    "and baseline backtest results. No database writes happen here."
)
render_quick_start_demo()
render_historical_csv_preview()
render_recent_historical_batches()

# Render the backtest comparison dashboard
render_historical_dashboard()
