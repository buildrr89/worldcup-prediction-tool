"""Unit tests for the scoring / evaluation math layer (`src/scoring.py`).

Standard library `unittest` only. Run from the repo root:

    python3 -m unittest tests/test_scoring.py
"""

import sys
import unittest
from pathlib import Path

# Make imports robust regardless of the current working directory by putting
# the project root (parent of this file's `tests/` dir) on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scoring import (
    actual_result_to_one_hot,
    brier_score,
    compare_prediction_to_baseline,
    log_loss,
    validate_probabilities,
)


VALID_PROBS = {"home": 0.45, "draw": 0.27, "away": 0.28}


class TestValidateProbabilities(unittest.TestCase):
    def test_valid_probabilities_pass(self):
        """A valid distribution is returned cleaned."""
        result = validate_probabilities(VALID_PROBS)
        self.assertEqual(result, VALID_PROBS)

    def test_missing_key_raises(self):
        """A distribution missing an outcome key raises ValueError."""
        with self.assertRaises(ValueError):
            validate_probabilities({"home": 0.5, "draw": 0.5})

    def test_non_summing_probabilities_raise(self):
        """Probabilities that do not sum to ~1.0 raise ValueError."""
        with self.assertRaises(ValueError):
            validate_probabilities({"home": 0.5, "draw": 0.5, "away": 0.5})


class TestActualResultToOneHot(unittest.TestCase):
    def test_one_hot_values(self):
        """home/draw/away each map to the correct one-hot dict."""
        self.assertEqual(
            actual_result_to_one_hot("home"),
            {"home": 1.0, "draw": 0.0, "away": 0.0},
        )
        self.assertEqual(
            actual_result_to_one_hot("draw"),
            {"home": 0.0, "draw": 1.0, "away": 0.0},
        )
        self.assertEqual(
            actual_result_to_one_hot("away"),
            {"home": 0.0, "draw": 0.0, "away": 1.0},
        )

    def test_invalid_result_raises(self):
        """An unknown actual result raises ValueError."""
        with self.assertRaises(ValueError):
            actual_result_to_one_hot("win")


class TestBrierScore(unittest.TestCase):
    def test_perfect_prediction_scores_zero(self):
        """A fully-confident correct prediction scores 0.0."""
        perfect = {"home": 1.0, "draw": 0.0, "away": 0.0}
        self.assertAlmostEqual(brier_score(perfect, "home"), 0.0, places=9)

    def test_worse_prediction_scores_higher(self):
        """A prediction further from the truth has a higher Brier score."""
        better = {"home": 0.70, "draw": 0.20, "away": 0.10}
        worse = {"home": 0.20, "draw": 0.20, "away": 0.60}
        self.assertGreater(
            brier_score(worse, "home"), brier_score(better, "home")
        )


class TestLogLoss(unittest.TestCase):
    def test_good_log_loss_lower_than_bad(self):
        """A confident correct prediction beats a confident wrong one."""
        good = {"home": 0.90, "draw": 0.05, "away": 0.05}
        bad = {"home": 0.05, "draw": 0.05, "away": 0.90}
        self.assertLess(log_loss(good, "home"), log_loss(bad, "home"))

    def test_invalid_epsilon_raises(self):
        """An out-of-range epsilon raises ValueError."""
        with self.assertRaises(ValueError):
            log_loss(VALID_PROBS, "home", epsilon=0.5)
        with self.assertRaises(ValueError):
            log_loss(VALID_PROBS, "home", epsilon=-0.1)
        with self.assertRaises(ValueError):
            log_loss(VALID_PROBS, "home", epsilon="0.01")


class TestComparePredictionToBaseline(unittest.TestCase):
    def test_returns_all_required_keys(self):
        """The comparison dict contains every documented key."""
        result = compare_prediction_to_baseline(
            VALID_PROBS, VALID_PROBS, "home"
        )
        expected_keys = {
            "prediction_brier",
            "baseline_brier",
            "brier_delta",
            "prediction_log_loss",
            "baseline_log_loss",
            "log_loss_delta",
            "prediction_improved_brier",
            "prediction_improved_log_loss",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_marks_improvement_when_prediction_beats_baseline(self):
        """A sharper correct prediction is marked as an improvement."""
        prediction = {"home": 0.70, "draw": 0.18, "away": 0.12}
        baseline = {"home": 0.45, "draw": 0.27, "away": 0.28}
        result = compare_prediction_to_baseline(prediction, baseline, "home")

        self.assertTrue(result["prediction_improved_brier"])
        self.assertTrue(result["prediction_improved_log_loss"])
        self.assertLess(result["brier_delta"], 0.0)
        self.assertLess(result["log_loss_delta"], 0.0)

    def test_marks_no_improvement_when_prediction_worse(self):
        """A prediction that moved away from the truth is not an improvement."""
        prediction = {"home": 0.20, "draw": 0.20, "away": 0.60}
        baseline = {"home": 0.45, "draw": 0.27, "away": 0.28}
        result = compare_prediction_to_baseline(prediction, baseline, "home")

        self.assertFalse(result["prediction_improved_brier"])
        self.assertFalse(result["prediction_improved_log_loss"])
        self.assertGreater(result["brier_delta"], 0.0)
        self.assertGreater(result["log_loss_delta"], 0.0)


if __name__ == "__main__":
    unittest.main()
