"""Streamlit UI components for uploading and previewing historical CSV files."""

import streamlit as st

from src.db import (
    save_historical_import,
    list_historical_import_batches,
    list_historical_matches,
)
from src.importers.football_data_csv import (
    load_csv_file,
    summarise_historical_matches,
    backtest_baseline,
)
from src.ui.formatting import _pct


def render_historical_csv_preview() -> None:
    """Render the file uploader, odds prefix selection, parsed matches, metrics preview, and save button."""
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

            # 4. Show clear messages: no DB writes happen yet, preview only, skipped rows
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
            st.error(str(error))


def render_recent_historical_batches() -> None:
    """Render the table of recent historical import batches and their details."""
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
