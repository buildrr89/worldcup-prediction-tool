"""Formatting and presentation helpers for the Streamlit UI."""


def _pct(value: float) -> str:
    """Format a probability (0.0–1.0) as a readable percentage string."""
    return f"{value * 100:.1f}%"
