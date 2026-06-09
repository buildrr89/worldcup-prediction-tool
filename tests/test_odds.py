"""Unit tests for the odds de-vig math layer (`src/odds.py`).

Standard library `unittest` only. Run from the repo root:

    python3 -m unittest tests/test_odds.py
"""

import sys
import unittest
from pathlib import Path

# Make imports robust regardless of the current working directory by putting
# the project root (parent of this file's `tests/` dir) on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.odds import decimal_odds_to_implied_probabilities


class TestDecimalOddsToImpliedProbabilities(unittest.TestCase):
    def test_normal_1x2_market(self):
        """A typical 1X2 market de-vigs to a valid baseline."""
        result = decimal_odds_to_implied_probabilities(2.10, 3.40, 3.60)

        # Overround is the bookmaker margin baked in — should exceed 1.0.
        self.assertGreater(result["overround"], 1.0)
        self.assertAlmostEqual(result["margin"], result["overround"] - 1.0)

        # Raw probabilities are 1 / odds.
        self.assertAlmostEqual(result["raw_home"], 1 / 2.10)
        self.assertAlmostEqual(result["raw_draw"], 1 / 3.40)
        self.assertAlmostEqual(result["raw_away"], 1 / 3.60)

        # De-vigged probabilities are each raw value over the overround.
        self.assertAlmostEqual(result["home"], result["raw_home"] / result["overround"])
        self.assertAlmostEqual(result["draw"], result["raw_draw"] / result["overround"])
        self.assertAlmostEqual(result["away"], result["raw_away"] / result["overround"])

        # The home favourite keeps the highest probability.
        self.assertGreater(result["home"], result["draw"])
        self.assertGreater(result["home"], result["away"])

    def test_heavy_favourite_market(self):
        """A heavy favourite gets a high de-vigged probability."""
        result = decimal_odds_to_implied_probabilities(1.10, 9.00, 21.00)

        self.assertGreater(result["home"], 0.85)
        self.assertGreater(result["home"], result["draw"])
        self.assertGreater(result["home"], result["away"])
        self.assertGreater(result["overround"], 1.0)

    def test_probabilities_sum_to_one(self):
        """De-vigged home + draw + away sum to approximately 1.0."""
        for odds in [(2.10, 3.40, 3.60), (1.10, 9.00, 21.00), (2.50, 3.25, 2.90)]:
            result = decimal_odds_to_implied_probabilities(*odds)
            total = result["home"] + result["draw"] + result["away"]
            self.assertAlmostEqual(total, 1.0, places=9)

    def test_invalid_odds_not_greater_than_one(self):
        """Odds <= 1.0 raise ValueError."""
        with self.assertRaises(ValueError):
            decimal_odds_to_implied_probabilities(1.0, 3.40, 3.60)
        with self.assertRaises(ValueError):
            decimal_odds_to_implied_probabilities(2.10, 0.5, 3.60)
        with self.assertRaises(ValueError):
            decimal_odds_to_implied_probabilities(2.10, 3.40, -2.0)

    def test_non_numeric_odds(self):
        """Non-numeric odds raise ValueError."""
        with self.assertRaises(ValueError):
            decimal_odds_to_implied_probabilities("2.10", 3.40, 3.60)
        with self.assertRaises(ValueError):
            decimal_odds_to_implied_probabilities(2.10, None, 3.60)
        with self.assertRaises(ValueError):
            decimal_odds_to_implied_probabilities(2.10, 3.40, True)


if __name__ == "__main__":
    unittest.main()
