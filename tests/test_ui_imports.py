"""Smoke tests for importing UI modules."""

import unittest

try:
    import streamlit as st  # noqa: F401
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


@unittest.skipUnless(HAS_STREAMLIT, "Streamlit is not installed in this environment")
class TestUIImports(unittest.TestCase):
    """Verify that UI modules import correctly and define required render functions."""

    def test_ui_render_functions_exist(self):
        """Import each UI module and verify expected functions exist."""
        from src.ui.formatting import _pct
        from src.ui.manual_prediction import render_manual_prediction
        from src.ui.saved_predictions import (
            render_save_prediction,
            render_recent_predictions,
            render_score_saved_prediction,
            render_recent_scored_predictions,
        )
        from src.ui.historical_csv import (
            render_historical_csv_preview,
            render_recent_historical_batches,
        )
        from src.ui.historical_dashboard import render_historical_dashboard
        from src.ui.demo import render_quick_start_demo
        from src.ui.prediction_performance import render_prediction_performance_dashboard

        self.assertTrue(callable(_pct))
        self.assertTrue(callable(render_manual_prediction))
        self.assertTrue(callable(render_save_prediction))
        self.assertTrue(callable(render_recent_predictions))
        self.assertTrue(callable(render_score_saved_prediction))
        self.assertTrue(callable(render_recent_scored_predictions))
        self.assertTrue(callable(render_historical_csv_preview))
        self.assertTrue(callable(render_recent_historical_batches))
        self.assertTrue(callable(render_historical_dashboard))
        self.assertTrue(callable(render_quick_start_demo))
        self.assertTrue(callable(render_prediction_performance_dashboard))
