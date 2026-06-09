"""Unit tests for the deterministic predictor layer (`src/predictor.py`).

Standard library `unittest` only. Run from the repo root:

    python3 -m unittest tests/test_predictor.py
"""

import sys
import unittest
from pathlib import Path

# Make imports robust regardless of the current working directory by putting
# the project root (parent of this file's `tests/` dir) on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.predictor import blend_probabilities


BASELINE = {"home": 0.45, "draw": 0.27, "away": 0.28}


class TestBlendProbabilities(unittest.TestCase):
    def test_no_factors_returns_close_to_baseline(self):
        """With no factors, the output should match the baseline."""
        result = blend_probabilities(BASELINE)

        self.assertAlmostEqual(result["home"], BASELINE["home"], places=9)
        self.assertAlmostEqual(result["draw"], BASELINE["draw"], places=9)
        self.assertAlmostEqual(result["away"], BASELINE["away"], places=9)
        self.assertEqual(result["applied_factors"], [])
        # The original baseline is preserved in the return value.
        self.assertEqual(result["baseline"], BASELINE)

    def test_none_factors_treated_as_empty(self):
        """factors=None behaves the same as no factors."""
        result = blend_probabilities(BASELINE, None)
        self.assertAlmostEqual(result["home"], BASELINE["home"], places=9)
        self.assertEqual(result["applied_factors"], [])

    def test_positive_home_factor_increases_home(self):
        """A positive home factor raises the home probability."""
        factors = [{"target": "home", "direction": "positive",
                    "magnitude": 1.0, "weight": 1.0, "note": "strong form"}]
        result = blend_probabilities(BASELINE, factors)

        self.assertGreater(result["home"], BASELINE["home"])
        self.assertEqual(len(result["applied_factors"]), 1)
        self.assertGreater(result["applied_factors"][0]["shift"], 0)

    def test_negative_away_factor_decreases_away(self):
        """A negative away factor lowers the away probability."""
        factors = [{"target": "away", "direction": "negative",
                    "magnitude": 1.0, "weight": 1.0, "note": "key injury"}]
        result = blend_probabilities(BASELINE, factors)

        self.assertLess(result["away"], BASELINE["away"])
        self.assertLess(result["applied_factors"][0]["shift"], 0)

    def test_output_always_sums_to_one(self):
        """Output home + draw + away always sums to approximately 1.0."""
        factor_sets = [
            None,
            [{"target": "home", "direction": "positive", "magnitude": 0.8, "weight": 0.5}],
            [{"target": "away", "direction": "negative", "magnitude": 1.0, "weight": 1.0}],
            [{"target": "draw", "direction": "positive", "magnitude": 0.3, "weight": 0.9}],
        ]
        for factors in factor_sets:
            result = blend_probabilities(BASELINE, factors)
            total = result["home"] + result["draw"] + result["away"]
            self.assertAlmostEqual(total, 1.0, places=9)

    def test_multiple_factors_normalise_correctly(self):
        """Several factors still produce a valid normalised distribution."""
        factors = [
            {"target": "home", "direction": "positive", "magnitude": 0.9, "weight": 0.8},
            {"target": "away", "direction": "negative", "magnitude": 0.7, "weight": 0.6},
            {"target": "draw", "direction": "positive", "magnitude": 0.4, "weight": 1.0},
        ]
        result = blend_probabilities(BASELINE, factors)

        total = result["home"] + result["draw"] + result["away"]
        self.assertAlmostEqual(total, 1.0, places=9)
        self.assertEqual(len(result["applied_factors"]), 3)
        for outcome in ("home", "draw", "away"):
            self.assertGreaterEqual(result[outcome], 0.0)

    def test_extreme_negative_factor_clamps_to_minimum(self):
        """A huge negative shift is clamped to a small positive probability."""
        factors = [{"target": "away", "direction": "negative",
                    "magnitude": 1.0, "weight": 1.0}]
        # Max shift large enough to drive raw away below zero before clamping.
        result = blend_probabilities(BASELINE, factors, max_total_shift=0.5)

        self.assertGreater(result["away"], 0.0)
        total = result["home"] + result["draw"] + result["away"]
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_invalid_baseline_missing_key_raises(self):
        """A baseline missing an outcome key raises ValueError."""
        with self.assertRaises(ValueError):
            blend_probabilities({"home": 0.5, "draw": 0.5})

    def test_invalid_baseline_non_numeric_raises(self):
        """A non-numeric baseline probability raises ValueError."""
        with self.assertRaises(ValueError):
            blend_probabilities({"home": "0.45", "draw": 0.27, "away": 0.28})

    def test_invalid_baseline_negative_raises(self):
        """A negative baseline probability raises ValueError."""
        with self.assertRaises(ValueError):
            blend_probabilities({"home": -0.1, "draw": 0.5, "away": 0.6})

    def test_invalid_baseline_sum_raises(self):
        """A baseline that does not sum to ~1.0 raises ValueError."""
        with self.assertRaises(ValueError):
            blend_probabilities({"home": 0.5, "draw": 0.5, "away": 0.5})

    def test_invalid_max_total_shift_raises(self):
        """An out-of-range max_total_shift raises ValueError."""
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, None, max_total_shift=0.9)
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, None, max_total_shift=-0.1)
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, None, max_total_shift="0.1")

    def test_invalid_factor_target_raises(self):
        """An invalid factor target raises ValueError."""
        factors = [{"target": "win", "direction": "positive",
                    "magnitude": 0.5, "weight": 0.5}]
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, factors)

    def test_invalid_factor_direction_raises(self):
        """An invalid factor direction raises ValueError."""
        factors = [{"target": "home", "direction": "up",
                    "magnitude": 0.5, "weight": 0.5}]
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, factors)

    def test_invalid_factor_magnitude_or_weight_raises(self):
        """An out-of-range magnitude or weight raises ValueError."""
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, [{"target": "home",
                "direction": "positive", "magnitude": 1.5, "weight": 0.5}])
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, [{"target": "home",
                "direction": "positive", "magnitude": 0.5, "weight": 2.0}])
        with self.assertRaises(ValueError):
            blend_probabilities(BASELINE, [{"target": "home",
                "direction": "positive", "magnitude": "0.5", "weight": 0.5}])


if __name__ == "__main__":
    unittest.main()
