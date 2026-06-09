"""Streamlit UI components for the quick-start demo."""

from pathlib import Path
import streamlit as st


def render_quick_start_demo() -> None:
    """Render the quick-start demo explanation and sample CSV download button."""
    st.subheader("Quick-start demo")
    st.write(
        "The included sample CSV is synthetic, containing fictional matches, results, and odds, "
        "and is legally safe for testing."
    )

    sample_path = Path("sample_data/football_data_sample.csv")
    if sample_path.exists():
        try:
            sample_data = sample_path.read_text(encoding="utf-8")
            st.download_button(
                label="Download sample CSV",
                data=sample_data,
                file_name="football_data_sample.csv",
                mime="text/csv",
                key="download_sample_csv_button"
            )
        except Exception as e:
            st.warning(f"Error reading sample CSV file: {e}")
    else:
        st.warning("⚠️ Synthetic sample CSV file `sample_data/football_data_sample.csv` is missing.")

    st.markdown(
        "**How to use the demo:**\n"
        "1. **Download the sample CSV** using the button above.\n"
        "2. **Upload it** in the **Upload historical CSV file** section below.\n"
        "3. **Preview results** in-memory (margin, Brier score, and Log Loss).\n"
        "4. Optionally **save parsed records locally** to the database."
    )
