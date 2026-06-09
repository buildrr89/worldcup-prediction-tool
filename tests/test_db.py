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


class TestSchemaMigration(DBTestCase):
    def test_scoring_columns_exist(self):
        """init_db creates predictions table with the 8 new scoring columns."""
        conn = db.get_connection()
        try:
            row = conn.execute("PRAGMA table_info(predictions)").fetchall()
            columns = {r[1] for r in row}
        finally:
            conn.close()

        expected_cols = [
            "actual_result",
            "prediction_brier",
            "baseline_brier",
            "brier_delta",
            "prediction_log_loss",
            "baseline_log_loss",
            "log_loss_delta",
            "scored_at",
        ]
        for col in expected_cols:
            self.assertIn(col, columns)

    def test_init_db_is_idempotent_with_columns(self):
        """Calling init_db multiple times does not raise errors or duplicate columns."""
        db.init_db()
        db.init_db()
        conn = db.get_connection()
        try:
            row = conn.execute("PRAGMA table_info(predictions)").fetchall()
            columns = [r[1] for r in row]
        finally:
            conn.close()
        self.assertEqual(columns.count("actual_result"), 1)


class TestGetPredictionForScoring(DBTestCase):
    def test_returns_prediction_with_baseline(self):
        match = {"home_team": "Brazil", "away_team": "Croatia"}
        flow = db.save_prediction_flow(match, VALID_ODDS_RESULT, [], VALID_PREDICTION)
        pred_id = flow["prediction_id"]

        res = db.get_prediction_for_scoring(pred_id)
        self.assertEqual(res["id"], pred_id)
        self.assertEqual(res["match_id"], flow["match_id"])
        self.assertEqual(res["home_probability"], 0.50)
        self.assertEqual(res["baseline"], VALID_PREDICTION["baseline"])
        self.assertIsNone(res["actual_result"])

    def test_missing_baseline_raises_value_error(self):
        # Create a prediction manually in DB that has no baseline in reasoning_json
        match_id = self._new_match_id()
        conn = db.get_connection()
        try:
            cur = conn.execute(
                """
                INSERT INTO predictions (match_id, home_probability, draw_probability, away_probability, reasoning_json)
                VALUES (?, 0.5, 0.3, 0.2, ?)
                """,
                (match_id, json.dumps({"explanation": "no baseline here"})),
            )
            pred_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(ValueError) as ctx:
            db.get_prediction_for_scoring(pred_id)
        self.assertIn("baseline is missing", str(ctx.exception))

    def test_invalid_prediction_id_raises(self):
        with self.assertRaises(ValueError):
            db.get_prediction_for_scoring(9999)
        with self.assertRaises(ValueError):
            db.get_prediction_for_scoring("not-int")


class TestScorePrediction(DBTestCase):
    def test_updates_db_and_returns_scores(self):
        match = {"home_team": "Brazil", "away_team": "Croatia"}
        flow = db.save_prediction_flow(match, VALID_ODDS_RESULT, [], VALID_PREDICTION)
        pred_id = flow["prediction_id"]

        res = db.score_prediction(pred_id, "home")
        self.assertEqual(res["prediction_id"], pred_id)
        self.assertEqual(res["actual_result"], "home")

        self.assertIn("prediction_brier", res)
        self.assertIn("baseline_brier", res)
        self.assertIn("brier_delta", res)
        self.assertIn("prediction_log_loss", res)
        self.assertIn("baseline_log_loss", res)
        self.assertIn("log_loss_delta", res)
        self.assertIn("prediction_improved_brier", res)
        self.assertIn("prediction_improved_log_loss", res)

        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM predictions WHERE id = ?", (pred_id,)).fetchone()
        finally:
            conn.close()

        self.assertEqual(row["actual_result"], "home")
        self.assertEqual(row["prediction_brier"], res["prediction_brier"])
        self.assertEqual(row["baseline_brier"], res["baseline_brier"])
        self.assertIsNotNone(row["scored_at"])

    def test_invalid_actual_result_raises(self):
        match = {"home_team": "Brazil", "away_team": "Croatia"}
        flow = db.save_prediction_flow(match, VALID_ODDS_RESULT, [], VALID_PREDICTION)
        pred_id = flow["prediction_id"]

        with self.assertRaises(ValueError):
            db.score_prediction(pred_id, "invalid_result")


class TestListScoredAndUnscored(DBTestCase):
    def test_lists_unscored_and_scored_predictions(self):
        self.assertEqual(len(db.list_unscored_predictions()), 0)
        self.assertEqual(len(db.list_scored_predictions()), 0)

        match1 = {"home_team": "Brazil", "away_team": "Croatia"}
        flow1 = db.save_prediction_flow(match1, VALID_ODDS_RESULT, [], VALID_PREDICTION)

        match2 = {"home_team": "France", "away_team": "Spain"}
        flow2 = db.save_prediction_flow(match2, VALID_ODDS_RESULT, [], VALID_PREDICTION)

        unscored = db.list_unscored_predictions()
        self.assertEqual(len(unscored), 2)
        self.assertEqual(unscored[0]["home_team"], "France")
        self.assertEqual(unscored[1]["home_team"], "Brazil")
        self.assertIn("prediction_id", unscored[0])
        self.assertIn("match_id", unscored[0])
        self.assertIn("home_probability", unscored[0])
        self.assertIn("draw_probability", unscored[0])
        self.assertIn("away_probability", unscored[0])
        self.assertIn("created_at", unscored[0])

        db.score_prediction(flow1["prediction_id"], "draw")

        unscored = db.list_unscored_predictions()
        scored = db.list_scored_predictions()
        self.assertEqual(len(unscored), 1)
        self.assertEqual(len(scored), 1)

        self.assertEqual(unscored[0]["prediction_id"], flow2["prediction_id"])
        self.assertEqual(scored[0]["prediction_id"], flow1["prediction_id"])
        self.assertEqual(scored[0]["actual_result"], "draw")

        self.assertIn("prediction_brier", scored[0])
        self.assertIn("baseline_brier", scored[0])
        self.assertIn("brier_delta", scored[0])
        self.assertIn("prediction_log_loss", scored[0])
        self.assertIn("baseline_log_loss", scored[0])
        self.assertIn("log_loss_delta", scored[0])
        self.assertIsNotNone(scored[0]["scored_at"])


class TestHistoricalImportPersistence(DBTestCase):
    def setUp(self):
        super().setUp()
        self.valid_match_data = {
            "date": "18/12/2022",
            "home_team": "Argentina",
            "away_team": "France",
            "actual_result": "draw",
            "home_decimal_odds": 2.80,
            "draw_decimal_odds": 3.00,
            "away_decimal_odds": 2.80,
            "baseline": {"home": 0.33, "draw": 0.34, "away": 0.33},
            "margin": 0.05,
            "source": "football-data.co.uk",
            "odds_prefix": "B365",
        }

    def test_1_init_db_creates_historical_tables_and_index(self):
        """init_db creates historical_import_batches, historical_matches and the unique index."""
        conn = db.get_connection()
        try:
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                ).fetchall()
            }
        finally:
            conn.close()
        self.assertIn("historical_import_batches", names)
        self.assertIn("historical_matches", names)
        self.assertIn("idx_historical_matches_unique", indexes)

    def test_2_create_historical_import_batch(self):
        """create_historical_import_batch returns a valid integer ID and saves columns correctly."""
        summary = {"match_count": 5, "average_margin": 0.06}
        backtest = {"average_brier": 0.42, "average_log_loss": 0.75}
        batch_id = db.create_historical_import_batch(
            source="football-data.co.uk",
            odds_prefix="B365",
            file_name="test.csv",
            summary=summary,
            backtest=backtest,
        )
        self.assertIsInstance(batch_id, int)
        self.assertGreater(batch_id, 0)

        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM historical_import_batches WHERE id = ?", (batch_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row["source"], "football-data.co.uk")
        self.assertEqual(row["odds_prefix"], "B365")
        self.assertEqual(row["file_name"], "test.csv")
        self.assertEqual(row["match_count"], 5)
        self.assertAlmostEqual(row["average_margin"], 0.06)
        self.assertAlmostEqual(row["average_brier"], 0.42)
        self.assertAlmostEqual(row["average_log_loss"], 0.75)
        self.assertIsNotNone(row["created_at"])

    def test_3_create_historical_match(self):
        """create_historical_match saves one parsed match correctly."""
        summary = {"match_count": 1, "average_margin": 0.05}
        backtest = {"average_brier": 0.25, "average_log_loss": 0.50}
        batch_id = db.create_historical_import_batch(
            source="football-data.co.uk",
            odds_prefix="B365",
            file_name="test.csv",
            summary=summary,
            backtest=backtest,
        )
        match_id = db.create_historical_match(batch_id, self.valid_match_data)
        self.assertIsInstance(match_id, int)
        self.assertGreater(match_id, 0)

        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM historical_matches WHERE id = ?", (match_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row["batch_id"], batch_id)
        self.assertEqual(row["match_date"], "18/12/2022")
        self.assertEqual(row["home_team"], "Argentina")
        self.assertEqual(row["away_team"], "France")
        self.assertEqual(row["actual_result"], "draw")
        self.assertEqual(row["home_decimal_odds"], 2.80)
        self.assertEqual(row["baseline_home"], 0.33)
        self.assertEqual(row["baseline_draw"], 0.34)
        self.assertEqual(row["baseline_away"], 0.33)
        self.assertEqual(row["margin"], 0.05)

    def test_4_save_historical_import_valid(self):
        """save_historical_import creates one batch and matches and returns metrics."""
        matches = [self.valid_match_data]
        res = db.save_historical_import(matches, "B365", "import.csv")
        self.assertIn("batch_id", res)
        self.assertIn("match_ids", res)
        self.assertEqual(res["match_count"], 1)
        self.assertAlmostEqual(res["average_margin"], 0.05)
        self.assertGreater(res["average_brier"], 0.0)
        self.assertGreater(res["average_log_loss"], 0.0)

        conn = db.get_connection()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM historical_import_batches").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM historical_matches").fetchone()[0], 1)
        finally:
            conn.close()

    def test_5_list_historical_import_batches(self):
        """list_historical_import_batches returns saved batches."""
        db.save_historical_import([self.valid_match_data], "B365", "import1.csv")
        db.save_historical_import([self.valid_match_data], "B365", "import2.csv")

        batches = db.list_historical_import_batches()
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0]["file_name"], "import2.csv")
        self.assertEqual(batches[1]["file_name"], "import1.csv")

    def test_6_list_historical_matches(self):
        """list_historical_matches returns matches for a batch."""
        res = db.save_historical_import([self.valid_match_data], "B365", "import.csv")
        batch_id = res["batch_id"]

        matches = db.list_historical_matches(batch_id)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["home_team"], "Argentina")
        self.assertEqual(matches[0]["match_date"], "18/12/2022")

    def test_7_empty_historical_import_raises(self):
        """save_historical_import raises ValueError on empty match list."""
        with self.assertRaises(ValueError):
            db.save_historical_import([], "B365")

    def test_8_invalid_match_missing_baseline_raises(self):
        """create_historical_match raises ValueError when match is missing required keys or baseline."""
        invalid_match = self.valid_match_data.copy()
        del invalid_match["baseline"]
        with self.assertRaises(ValueError):
            db.create_historical_match(1, invalid_match)

    def test_9_failed_import_rolls_back(self):
        """Failed import rolls back all batch and match rows if a later match is invalid."""
        invalid_match = self.valid_match_data.copy()
        del invalid_match["home_team"]
        matches = [self.valid_match_data, invalid_match]

        with self.assertRaises(ValueError):
            db.save_historical_import(matches, "B365")

        conn = db.get_connection()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM historical_import_batches").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM historical_matches").fetchone()[0], 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
