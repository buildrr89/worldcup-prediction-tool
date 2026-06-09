"""Unit tests for the SQLite persistence layer (`src/db.py`).

Standard library `unittest` only. These tests never touch the real
`data/worldcup.db`: each test points `db.DB_PATH` at a fresh temporary file via
`tempfile.TemporaryDirectory`, calls `init_db()`, and restores the original
path on teardown. Run from the repo root:

    python3 -m unittest tests/test_db.py
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Make imports robust regardless of the current working directory by putting
# the project root (parent of this file's `tests/` dir) on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import db


VALID_ODDS_RESULT = {
    "home_decimal_odds": 2.20,
    "draw_decimal_odds": 3.30,
    "away_decimal_odds": 3.20,
    "home": 0.45,
    "draw": 0.30,
    "away": 0.25,
}

VALID_PREDICTION = {
    "home": 0.50,
    "draw": 0.28,
    "away": 0.22,
    "baseline": {"home": 0.45, "draw": 0.30, "away": 0.25},
    "applied_factors": [
        {"target": "home", "direction": "positive", "magnitude": 0.5,
         "weight": 0.5, "shift": 0.0375, "note": "home form"}
    ],
    "max_total_shift": 0.15,
    "explanation": "test explanation",
}

VALID_FACTOR = {
    "target": "home",
    "direction": "positive",
    "magnitude": 0.5,
    "weight": 0.5,
    "note": "strong home form",
}


class DBTestCase(unittest.TestCase):
    """Base case: redirect `db.DB_PATH` to a temp DB and init the schema."""

    def setUp(self):
        self._original_db_path = db.DB_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self._tmpdir.name) / "test_worldcup.db"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self._original_db_path
        self._tmpdir.cleanup()

    def _new_match_id(self):
        return db.create_match("Brazil", "Croatia")


class TestInitDb(DBTestCase):
    def test_init_db_creates_all_tables(self):
        """init_db creates the five core tables in a temporary DB."""
        conn = db.get_connection()
        try:
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        finally:
            conn.close()
        for table in ("teams", "matches", "signals", "factors", "predictions"):
            self.assertIn(table, names)


class TestCreateMatch(DBTestCase):
    def test_returns_integer_id(self):
        match_id = db.create_match("Brazil", "Croatia", "2026-06-20T18:00", "QF")
        self.assertIsInstance(match_id, int)
        self.assertGreater(match_id, 0)

    def test_empty_team_name_raises(self):
        with self.assertRaises(ValueError):
            db.create_match("", "Croatia")
        with self.assertRaises(ValueError):
            db.create_match("Brazil", "   ")


class TestCreateSignal(DBTestCase):
    def test_saves_odds_and_probabilities(self):
        match_id = self._new_match_id()
        signal_id = db.create_signal(match_id, VALID_ODDS_RESULT)
        self.assertIsInstance(signal_id, int)

        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM signals WHERE id = ?", (signal_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row["match_id"], match_id)
        self.assertEqual(row["home_decimal_odds"], 2.20)
        self.assertEqual(row["home_implied_prob"], 0.45)
        self.assertEqual(row["away_implied_prob"], 0.25)

    def test_invalid_match_id_raises(self):
        with self.assertRaises(ValueError):
            db.create_signal(0, VALID_ODDS_RESULT)


class TestCreateFactor(DBTestCase):
    def test_saves_research_factor(self):
        match_id = self._new_match_id()
        factor_id = db.create_factor(match_id, VALID_FACTOR)
        self.assertIsInstance(factor_id, int)

        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM factors WHERE id = ?", (factor_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row["team"], "home")
        self.assertEqual(row["factor_type"], "research")
        self.assertEqual(row["direction"], "positive")
        self.assertEqual(row["magnitude"], 0.5)
        # Weight has no column; it is preserved in the note text.
        self.assertIn("weight=0.5", row["note"])

    def test_invalid_match_id_raises(self):
        with self.assertRaises(ValueError):
            db.create_factor(-1, VALID_FACTOR)


class TestCreatePrediction(DBTestCase):
    def test_saves_prediction_json(self):
        match_id = self._new_match_id()
        prediction_id = db.create_prediction(match_id, VALID_PREDICTION)
        self.assertIsInstance(prediction_id, int)

        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM predictions WHERE id = ?", (prediction_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row["home_probability"], 0.50)
        reasoning = json.loads(row["reasoning_json"])
        self.assertIn("baseline", reasoning)
        self.assertIn("applied_factors", reasoning)
        self.assertEqual(reasoning["baseline"]["home"], 0.45)

    def test_invalid_match_id_raises(self):
        with self.assertRaises(ValueError):
            db.create_prediction("nope", VALID_PREDICTION)


class TestSavePredictionFlow(DBTestCase):
    def test_creates_match_signal_factors_prediction(self):
        match = {"home_team": "Brazil", "away_team": "Croatia", "stage": "QF"}
        result = db.save_prediction_flow(
            match, VALID_ODDS_RESULT, [VALID_FACTOR, VALID_FACTOR], VALID_PREDICTION
        )
        self.assertIn("match_id", result)
        self.assertIn("signal_id", result)
        self.assertEqual(len(result["factor_ids"]), 2)
        self.assertIn("prediction_id", result)

        conn = db.get_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0], 1
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 1
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM factors").fetchone()[0], 2
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0], 1
            )
        finally:
            conn.close()

    def test_invalid_match_rolls_back(self):
        """A bad match aborts the flow without leaving partial rows."""
        match = {"home_team": "", "away_team": "Croatia"}
        with self.assertRaises(ValueError):
            db.save_prediction_flow(
                match, VALID_ODDS_RESULT, [VALID_FACTOR], VALID_PREDICTION
            )
        conn = db.get_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0], 0
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0], 0
            )
        finally:
            conn.close()


class TestListRecentPredictions(DBTestCase):
    def test_returns_saved_prediction_rows(self):
        match = {"home_team": "Brazil", "away_team": "Croatia", "stage": "QF"}
        db.save_prediction_flow(match, VALID_ODDS_RESULT, [VALID_FACTOR], VALID_PREDICTION)

        rows = db.list_recent_predictions()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["home_team"], "Brazil")
        self.assertEqual(row["away_team"], "Croatia")
        self.assertEqual(row["home_probability"], 0.50)
        self.assertIn("created_at", row)

    def test_most_recent_first(self):
        db.save_prediction_flow(
            {"home_team": "Brazil", "away_team": "Croatia"},
            VALID_ODDS_RESULT, [], VALID_PREDICTION,
        )
        db.save_prediction_flow(
            {"home_team": "France", "away_team": "Spain"},
            VALID_ODDS_RESULT, [], VALID_PREDICTION,
        )
        rows = db.list_recent_predictions()
        self.assertEqual(rows[0]["home_team"], "France")


if __name__ == "__main__":
    unittest.main()
