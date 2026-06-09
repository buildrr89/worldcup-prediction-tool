"""SQLite foundation for the World Cup prediction research tool.

Local-first, standard library only. Provides a connection helper and an
`init_db()` that creates the five core tables. Run directly to initialize:

    python src/db.py
"""

import json
import sqlite3
from pathlib import Path

from src.scoring import actual_result_to_one_hot, compare_prediction_to_baseline

# Resolve paths relative to the project root (parent of this file's `src/` dir),
# so the DB lands in the same place regardless of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "worldcup.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled.

    Ensures the parent directory of ``DB_PATH`` exists before connecting. The
    path is read from the module-level ``DB_PATH`` at call time, so tests can
    point it at a temporary database by monkeypatching ``db.DB_PATH``.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    """Ensure a column exists on a table, adding it if missing. Idempotent."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cur.fetchall()}
    if column_name not in columns:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def init_db() -> None:
    """Create the five core tables if they do not already exist."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                fifa_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                kickoff_at TEXT,
                stage TEXT,
                status TEXT NOT NULL DEFAULT 'scheduled',
                home_score INTEGER,
                away_score INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                home_decimal_odds REAL,
                draw_decimal_odds REAL,
                away_decimal_odds REAL,
                home_implied_prob REAL,
                draw_implied_prob REAL,
                away_implied_prob REAL,
                captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS factors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                team TEXT,
                factor_type TEXT NOT NULL,
                direction TEXT NOT NULL,
                magnitude REAL NOT NULL,
                confidence TEXT NOT NULL DEFAULT 'medium',
                note TEXT NOT NULL,
                source_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                home_probability REAL NOT NULL,
                draw_probability REAL NOT NULL,
                away_probability REAL NOT NULL,
                recommended_angle TEXT,
                confidence TEXT NOT NULL DEFAULT 'medium',
                reasoning_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(id)
            )
            """
        )

        # Ensure new columns exist on predictions table for result scoring
        ensure_column(conn, "predictions", "actual_result", "TEXT")
        ensure_column(conn, "predictions", "prediction_brier", "REAL")
        ensure_column(conn, "predictions", "baseline_brier", "REAL")
        ensure_column(conn, "predictions", "brier_delta", "REAL")
        ensure_column(conn, "predictions", "prediction_log_loss", "REAL")
        ensure_column(conn, "predictions", "baseline_log_loss", "REAL")
        ensure_column(conn, "predictions", "log_loss_delta", "REAL")
        ensure_column(conn, "predictions", "scored_at", "TEXT")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL DEFAULT 'football-data.co.uk',
                odds_prefix TEXT NOT NULL,
                file_name TEXT,
                match_count INTEGER NOT NULL DEFAULT 0,
                average_margin REAL NOT NULL DEFAULT 0.0,
                average_brier REAL NOT NULL DEFAULT 0.0,
                average_log_loss REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'football-data.co.uk',
                odds_prefix TEXT NOT NULL,
                match_date TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                actual_result TEXT NOT NULL,
                home_decimal_odds REAL NOT NULL,
                draw_decimal_odds REAL NOT NULL,
                away_decimal_odds REAL NOT NULL,
                baseline_home REAL NOT NULL,
                baseline_draw REAL NOT NULL,
                baseline_away REAL NOT NULL,
                margin REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES historical_import_batches(id)
            )
            """
        )

        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_matches_unique
            ON historical_matches (batch_id, match_date, home_team, away_team, odds_prefix)
            """
        )

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Write / read helpers
#
# Manual, explicit SQLite persistence for the existing five tables. All SQL uses
# parameterized placeholders. Each `create_*` helper accepts an optional shared
# `conn`: when omitted it opens its own connection, commits, and closes; when
# provided it uses the caller's connection and leaves committing to the caller
# (so `save_prediction_flow` can wrap every insert in a single transaction).
# ---------------------------------------------------------------------------


def _validate_match_id(match_id) -> int:
    """Return ``match_id`` as an int, or raise ValueError if it is not a
    positive integer. bool is a subclass of int, so reject it explicitly."""
    if isinstance(match_id, bool) or not isinstance(match_id, int):
        raise ValueError(f"match_id must be an integer, got {match_id!r}")
    if match_id <= 0:
        raise ValueError(f"match_id must be positive, got {match_id!r}")
    return match_id


def create_match(
    home_team: str,
    away_team: str,
    kickoff_at: "str | None" = None,
    stage: "str | None" = None,
    conn: "sqlite3.Connection | None" = None,
) -> int:
    """Insert a fixture into ``matches`` and return its new id.

    ``home_team`` and ``away_team`` must be non-empty strings. ``status`` is
    left to the database default ('scheduled').
    """
    for name, value in (("home_team", home_team), ("away_team", away_team)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string, got {value!r}")

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO matches (home_team, away_team, kickoff_at, stage)
            VALUES (?, ?, ?, ?)
            """,
            (home_team.strip(), away_team.strip(), kickoff_at, stage),
        )
        if owns_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if owns_conn:
            conn.close()


def create_signal(
    match_id: int,
    odds_result: dict,
    source: str = "manual",
    conn: "sqlite3.Connection | None" = None,
) -> int:
    """Insert a bookmaker odds signal into ``signals`` and return its new id.

    ``odds_result`` is expected to carry both the original decimal odds and the
    de-vigged probabilities:
        home_decimal_odds / draw_decimal_odds / away_decimal_odds — the original
            odds (added by the caller; ``decimal_odds_to_implied_probabilities``
            does not preserve them).
        home / draw / away — the de-vigged implied probabilities.
    Missing decimal-odds keys are stored as NULL.
    """
    _validate_match_id(match_id)
    if not isinstance(odds_result, dict):
        raise ValueError(f"odds_result must be a dict, got {odds_result!r}")

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO signals (
                match_id, source,
                home_decimal_odds, draw_decimal_odds, away_decimal_odds,
                home_implied_prob, draw_implied_prob, away_implied_prob
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match_id,
                source,
                odds_result.get("home_decimal_odds"),
                odds_result.get("draw_decimal_odds"),
                odds_result.get("away_decimal_odds"),
                odds_result.get("home"),
                odds_result.get("draw"),
                odds_result.get("away"),
            ),
        )
        if owns_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if owns_conn:
            conn.close()


def create_factor(
    match_id: int,
    factor: dict,
    conn: "sqlite3.Connection | None" = None,
) -> int:
    """Insert one research factor into ``factors`` and return its new id.

    ``factor`` is the app/predictor factor shape (``target``, ``direction``,
    ``magnitude``, ``weight``, ``note``). It maps onto the schema as:
        target    -> team        (one of home/draw/away)
        (fixed)   -> factor_type  ('research')
        direction -> direction
        magnitude -> magnitude
        note      -> note         (the numeric ``weight`` is appended here, since
                                   the schema has no weight column — see DECISIONS).
    ``confidence`` is left to the database default ('medium').
    """
    _validate_match_id(match_id)
    if not isinstance(factor, dict):
        raise ValueError(f"factor must be a dict, got {factor!r}")

    note = factor.get("note") or ""
    weight = factor.get("weight")
    if weight is not None:
        # The schema has no weight column; preserve it in the note text so the
        # saved factor is not silently lossy.
        suffix = f"[weight={weight}]"
        note = f"{note} {suffix}".strip() if note else suffix

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO factors (
                match_id, team, factor_type, direction, magnitude, note
            )
            VALUES (?, ?, 'research', ?, ?, ?)
            """,
            (
                match_id,
                factor.get("target"),
                factor.get("direction"),
                factor.get("magnitude"),
                note,
            ),
        )
        if owns_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if owns_conn:
            conn.close()


def create_prediction(
    match_id: int,
    prediction: dict,
    conn: "sqlite3.Connection | None" = None,
) -> int:
    """Insert a blended prediction into ``predictions`` and return its new id.

    ``prediction`` is the ``blend_probabilities`` result (``home``/``draw``/
    ``away`` plus ``baseline`` and ``applied_factors``). The baseline and applied
    factors are serialised into ``reasoning_json`` via the standard-library
    ``json.dumps`` so the prediction stays transparent and inspectable.
    """
    _validate_match_id(match_id)
    if not isinstance(prediction, dict):
        raise ValueError(f"prediction must be a dict, got {prediction!r}")

    reasoning = {
        "baseline": prediction.get("baseline"),
        "applied_factors": prediction.get("applied_factors", []),
        "max_total_shift": prediction.get("max_total_shift"),
        "explanation": prediction.get("explanation"),
    }
    reasoning_json = json.dumps(reasoning)

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO predictions (
                match_id,
                home_probability, draw_probability, away_probability,
                recommended_angle, confidence, reasoning_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match_id,
                prediction.get("home"),
                prediction.get("draw"),
                prediction.get("away"),
                prediction.get("recommended_angle"),
                prediction.get("confidence", "medium"),
                reasoning_json,
            ),
        )
        if owns_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if owns_conn:
            conn.close()


def save_prediction_flow(
    match: dict,
    odds_result: dict,
    factors: "list[dict]",
    prediction: dict,
) -> dict:
    """Persist a full prediction flow (match, signal, factors, prediction).

    Runs every insert inside a single transaction so a failure rolls everything
    back rather than leaving a partial save. Returns the inserted ids:
        {"match_id", "signal_id", "factor_ids", "prediction_id"}.
    """
    conn = get_connection()
    try:
        match_id = create_match(
            match.get("home_team"),
            match.get("away_team"),
            match.get("kickoff_at"),
            match.get("stage"),
            conn=conn,
        )
        signal_id = create_signal(match_id, odds_result, conn=conn)
        factor_ids = [
            create_factor(match_id, factor, conn=conn) for factor in (factors or [])
        ]
        prediction_id = create_prediction(match_id, prediction, conn=conn)

        conn.commit()
        return {
            "match_id": match_id,
            "signal_id": signal_id,
            "factor_ids": factor_ids,
            "prediction_id": prediction_id,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_recent_predictions(limit: int = 10) -> "list[dict]":
    """Return recent predictions joined with their match, most recent first.

    A simple read helper for confirming saved records in the app.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                p.id AS prediction_id,
                p.match_id AS match_id,
                m.home_team AS home_team,
                m.away_team AS away_team,
                m.stage AS stage,
                p.home_probability AS home_probability,
                p.draw_probability AS draw_probability,
                p.away_probability AS away_probability,
                p.confidence AS confidence,
                p.created_at AS created_at
            FROM predictions p
            JOIN matches m ON m.id = p.match_id
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_prediction_for_scoring(prediction_id: int) -> dict:
    """Return enough data to score a prediction, loading it by ID.

    Raises ValueError if prediction_id is invalid, if prediction is not found,
    or if the baseline is missing from its reasoning_json.
    """
    if isinstance(prediction_id, bool) or not isinstance(prediction_id, int):
        raise ValueError(f"prediction_id must be an integer, got {prediction_id!r}")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT id, match_id, home_probability, draw_probability, away_probability,
                   actual_result, prediction_brier, baseline_brier, brier_delta,
                   prediction_log_loss, baseline_log_loss, log_loss_delta, scored_at,
                   reasoning_json
            FROM predictions
            WHERE id = ?
            """,
            (prediction_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Prediction #{prediction_id} not found")

        res = dict(row)
        reasoning = {}
        if res.get("reasoning_json"):
            try:
                reasoning = json.loads(res["reasoning_json"])
            except Exception as e:
                raise ValueError(
                    f"Failed to parse reasoning_json for prediction #{prediction_id}: {e}"
                )

        baseline = reasoning.get("baseline")
        if not baseline or not isinstance(baseline, dict):
            raise ValueError(
                f"Prediction #{prediction_id} cannot be scored because baseline is missing from reasoning_json"
            )

        res["baseline"] = baseline
        return res
    finally:
        conn.close()


def score_prediction(prediction_id: int, actual_result: str) -> dict:
    """Score a saved prediction against the bookmaker baseline.

    Validates actual_result, loads baseline and prediction probability,
    computes scores, and updates the row in the database.
    """
    # Validate result format/values (e.g. 'home', 'draw', 'away')
    actual_result_to_one_hot(actual_result)

    # Load prediction data (raises ValueError if not found or missing baseline)
    pred_data = get_prediction_for_scoring(prediction_id)

    prediction_probs = {
        "home": pred_data["home_probability"],
        "draw": pred_data["draw_probability"],
        "away": pred_data["away_probability"],
    }
    baseline_probs = pred_data["baseline"]

    # Compare prediction to baseline
    scores = compare_prediction_to_baseline(prediction_probs, baseline_probs, actual_result)

    # Update the database
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE predictions
            SET actual_result = ?,
                prediction_brier = ?,
                baseline_brier = ?,
                brier_delta = ?,
                prediction_log_loss = ?,
                baseline_log_loss = ?,
                log_loss_delta = ?,
                scored_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                actual_result,
                scores["prediction_brier"],
                scores["baseline_brier"],
                scores["brier_delta"],
                scores["prediction_log_loss"],
                scores["baseline_log_loss"],
                scores["log_loss_delta"],
                prediction_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "prediction_id": prediction_id,
        "actual_result": actual_result,
        "prediction_brier": scores["prediction_brier"],
        "baseline_brier": scores["baseline_brier"],
        "brier_delta": scores["brier_delta"],
        "prediction_log_loss": scores["prediction_log_loss"],
        "baseline_log_loss": scores["baseline_log_loss"],
        "log_loss_delta": scores["log_loss_delta"],
        "prediction_improved_brier": scores["prediction_improved_brier"],
        "prediction_improved_log_loss": scores["prediction_improved_log_loss"],
    }


def list_unscored_predictions(limit: int = 20) -> "list[dict]":
    """Return saved predictions that have not been scored yet, most recent first."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                p.id AS prediction_id,
                p.match_id AS match_id,
                m.home_team AS home_team,
                m.away_team AS away_team,
                m.stage AS stage,
                p.created_at AS created_at,
                p.home_probability AS home_probability,
                p.draw_probability AS draw_probability,
                p.away_probability AS away_probability
            FROM predictions p
            JOIN matches m ON m.id = p.match_id
            WHERE p.actual_result IS NULL
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_scored_predictions(limit: int = 20) -> "list[dict]":
    """Return scored predictions, most recent first."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                p.id AS prediction_id,
                p.match_id AS match_id,
                m.home_team AS home_team,
                m.away_team AS away_team,
                p.actual_result AS actual_result,
                p.prediction_brier AS prediction_brier,
                p.baseline_brier AS baseline_brier,
                p.brier_delta AS brier_delta,
                p.prediction_log_loss AS prediction_log_loss,
                p.baseline_log_loss AS baseline_log_loss,
                p.log_loss_delta AS log_loss_delta,
                p.scored_at AS scored_at
            FROM predictions p
            JOIN matches m ON m.id = p.match_id
            WHERE p.actual_result IS NOT NULL
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_historical_import_batch(
    source: str,
    odds_prefix: str,
    file_name: str | None,
    summary: dict,
    backtest: dict,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert one row into historical_import_batches and return its new id.

    Validate odds_prefix is a non-empty string.
    Use match_count, average_margin, average_brier, average_log_loss.
    """
    if not isinstance(odds_prefix, str) or not odds_prefix.strip():
        raise ValueError("odds_prefix must be a non-empty string")

    match_count = summary.get("match_count", 0)
    average_margin = summary.get("average_margin", 0.0)
    average_brier = backtest.get("average_brier", 0.0)
    average_log_loss = backtest.get("average_log_loss", 0.0)

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO historical_import_batches (
                source, odds_prefix, file_name, match_count, average_margin, average_brier, average_log_loss
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.strip() if source else "football-data.co.uk",
                odds_prefix.strip(),
                file_name,
                match_count,
                average_margin,
                average_brier,
                average_log_loss,
            ),
        )
        if owns_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if owns_conn:
            conn.close()


def create_historical_match(
    batch_id: int,
    match: dict,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert one parsed historical match into historical_matches and return its new id.

    Validate batch_id is positive integer.
    Validate required match fields exist.
    """
    if isinstance(batch_id, bool) or not isinstance(batch_id, int):
        raise ValueError(f"batch_id must be an integer, got {batch_id!r}")
    if batch_id <= 0:
        raise ValueError(f"batch_id must be positive, got {batch_id!r}")

    if not isinstance(match, dict):
        raise ValueError(f"match must be a dict, got {match!r}")

    required_keys = [
        "date", "home_team", "away_team", "actual_result",
        "home_decimal_odds", "draw_decimal_odds", "away_decimal_odds",
        "baseline", "margin"
    ]
    for key in required_keys:
        if key not in match:
            raise ValueError(f"Missing required match field: {key}")

    baseline = match["baseline"]
    if not isinstance(baseline, dict) or not all(k in baseline for k in ("home", "draw", "away")):
        raise ValueError("match['baseline'] must be a dict with keys 'home', 'draw', 'away'")

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO historical_matches (
                batch_id, source, odds_prefix, match_date, home_team, away_team, actual_result,
                home_decimal_odds, draw_decimal_odds, away_decimal_odds,
                baseline_home, baseline_draw, baseline_away, margin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                match.get("source", "football-data.co.uk"),
                match.get("odds_prefix", "B365"),
                match["date"],
                match["home_team"],
                match["away_team"],
                match["actual_result"],
                match["home_decimal_odds"],
                match["draw_decimal_odds"],
                match["away_decimal_odds"],
                baseline["home"],
                baseline["draw"],
                baseline["away"],
                match["margin"],
            ),
        )
        if owns_conn:
            conn.commit()
        return cur.lastrowid
    finally:
        if owns_conn:
            conn.close()


def save_historical_import(
    matches: list[dict],
    odds_prefix: str,
    file_name: str | None = None,
) -> dict:
    """Save a list of parsed matches to DB inside a single transaction.

    Use summarise_historical_matches and backtest_baseline from the importer module.
    Create batch.
    Insert all matches.
    """
    if not matches:
        raise ValueError("Matches list cannot be empty")

    from src.importers.football_data_csv import summarise_historical_matches, backtest_baseline

    summary = summarise_historical_matches(matches)
    backtest = backtest_baseline(matches)

    conn = get_connection()
    try:
        batch_id = create_historical_import_batch(
            source="football-data.co.uk",
            odds_prefix=odds_prefix,
            file_name=file_name,
            summary=summary,
            backtest=backtest,
            conn=conn,
        )

        match_ids = []
        for match in matches:
            match_id = create_historical_match(batch_id, match, conn=conn)
            match_ids.append(match_id)

        conn.commit()

        return {
            "batch_id": batch_id,
            "match_ids": match_ids,
            "match_count": summary["match_count"],
            "average_margin": summary["average_margin"],
            "average_brier": backtest["average_brier"],
            "average_log_loss": backtest["average_log_loss"],
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_historical_import_batches(limit: int = 10) -> list[dict]:
    """Return most recent batches."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, source, odds_prefix, file_name, match_count, average_margin, average_brier, average_log_loss, created_at
            FROM historical_import_batches
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_historical_matches(batch_id: int, limit: int = 20) -> list[dict]:
    """Return matches for a batch."""
    if isinstance(batch_id, bool) or not isinstance(batch_id, int):
        raise ValueError(f"batch_id must be an integer, got {batch_id!r}")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, batch_id, source, odds_prefix, match_date, home_team, away_team, actual_result,
                   home_decimal_odds, draw_decimal_odds, away_decimal_odds,
                   baseline_home, baseline_draw, baseline_away, margin, created_at
            FROM historical_matches
            WHERE batch_id = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (batch_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_historical_batch_summary(batch_id: int) -> dict:
    """Return one batch summary by ID, including result distribution.

    Raises ValueError if batch_id is invalid (not positive integer) or not found.
    """
    if isinstance(batch_id, bool) or not isinstance(batch_id, int):
        raise ValueError(f"batch_id must be an integer, got {batch_id!r}")
    if batch_id <= 0:
        raise ValueError(f"batch_id must be positive, got {batch_id!r}")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT id, source, odds_prefix, file_name, match_count, average_margin, average_brier, average_log_loss, created_at
            FROM historical_import_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Batch #{batch_id} not found")

        counts = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN actual_result = 'home' THEN 1 ELSE 0 END), 0) as home_wins,
                COALESCE(SUM(CASE WHEN actual_result = 'draw' THEN 1 ELSE 0 END), 0) as draws,
                COALESCE(SUM(CASE WHEN actual_result = 'away' THEN 1 ELSE 0 END), 0) as away_wins
            FROM historical_matches
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()

        res = dict(row)
        res["home_wins"] = counts["home_wins"]
        res["draws"] = counts["draws"]
        res["away_wins"] = counts["away_wins"]
        return res
    finally:
        conn.close()


def list_historical_batch_summaries(limit: int = 20) -> list[dict]:
    """Return recent batch summaries, newest first, with result distribution.

    Raises ValueError if limit is not a positive integer.
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(f"limit must be an integer, got {limit!r}")
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit!r}")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT 
                b.id, b.source, b.odds_prefix, b.file_name, b.match_count, b.average_margin, b.average_brier, b.average_log_loss, b.created_at,
                COALESCE(SUM(CASE WHEN m.actual_result = 'home' THEN 1 ELSE 0 END), 0) as home_wins,
                COALESCE(SUM(CASE WHEN m.actual_result = 'draw' THEN 1 ELSE 0 END), 0) as draws,
                COALESCE(SUM(CASE WHEN m.actual_result = 'away' THEN 1 ELSE 0 END), 0) as away_wins
            FROM historical_import_batches b
            LEFT JOIN historical_matches m ON b.id = m.batch_id
            GROUP BY b.id
            ORDER BY b.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def compare_historical_batches(batch_ids: list[int] | None = None) -> dict:
    """Compare saved historical CSV import batches.

    If batch_ids is None or empty, compare recent batches, limit 20.
    If provided, compare those batch IDs only.
    Raises ValueError on invalid batch id or if a batch ID doesn't exist.
    """
    if batch_ids is not None:
        if not isinstance(batch_ids, list):
            raise ValueError(f"batch_ids must be a list or None, got {batch_ids!r}")
        for b_id in batch_ids:
            if isinstance(b_id, bool) or not isinstance(b_id, int):
                raise ValueError(f"batch_id must be an integer, got {b_id!r}")
            if b_id <= 0:
                raise ValueError(f"batch_id must be positive, got {b_id!r}")

    if batch_ids:
        # Check if every batch_id exists. If not, raise ValueError.
        conn = get_connection()
        try:
            for b_id in batch_ids:
                exists = conn.execute(
                    "SELECT 1 FROM historical_import_batches WHERE id = ?", (b_id,)
                ).fetchone()
                if not exists:
                    raise ValueError(f"Batch #{b_id} not found")
        finally:
            conn.close()

        # Fetch summaries for specified batch_ids
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        try:
            placeholders = ",".join("?" for _ in batch_ids)
            rows = conn.execute(
                f"""
                SELECT 
                    b.id, b.source, b.odds_prefix, b.file_name, b.match_count, b.average_margin, b.average_brier, b.average_log_loss, b.created_at,
                    COALESCE(SUM(CASE WHEN m.actual_result = 'home' THEN 1 ELSE 0 END), 0) as home_wins,
                    COALESCE(SUM(CASE WHEN m.actual_result = 'draw' THEN 1 ELSE 0 END), 0) as draws,
                    COALESCE(SUM(CASE WHEN m.actual_result = 'away' THEN 1 ELSE 0 END), 0) as away_wins
                FROM historical_import_batches b
                LEFT JOIN historical_matches m ON b.id = m.batch_id
                WHERE b.id IN ({placeholders})
                GROUP BY b.id
                ORDER BY b.id DESC
                """,
                batch_ids,
            ).fetchall()
            batches = [dict(row) for row in rows]
        finally:
            conn.close()
    else:
        # Default to recent 20 batches
        batches = list_historical_batch_summaries(20)

    if not batches:
        return {
            "batch_count": 0,
            "batches": [],
            "best_brier_batch": None,
            "best_log_loss_batch": None,
            "lowest_margin_batch": None,
        }

    best_brier_batch = min(batches, key=lambda x: x["average_brier"])
    best_log_loss_batch = min(batches, key=lambda x: x["average_log_loss"])
    lowest_margin_batch = min(batches, key=lambda x: x["average_margin"])

    return {
        "batch_count": len(batches),
        "batches": batches,
        "best_brier_batch": best_brier_batch,
        "best_log_loss_batch": best_log_loss_batch,
        "lowest_margin_batch": lowest_margin_batch,
    }


def get_prediction_performance_summary() -> dict:
    """Return an aggregate calibration/performance summary for saved manual predictions.

    Compares manual predictions to the baseline.
    If no scored predictions exist, returns scored_count = 0 and None for averages/best/worst fields.
    Uses only predictions where scored_at IS NOT NULL.
    """
    conn = get_connection()
    try:
        count_row = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE scored_at IS NOT NULL"
        ).fetchone()
        scored_count = count_row[0] if count_row else 0

        if scored_count == 0:
            return {
                "scored_count": 0,
                "average_prediction_brier": None,
                "average_baseline_brier": None,
                "average_brier_delta": None,
                "average_prediction_log_loss": None,
                "average_baseline_log_loss": None,
                "average_log_loss_delta": None,
                "brier_improved_count": 0,
                "brier_worsened_count": 0,
                "brier_tied_count": 0,
                "log_loss_improved_count": 0,
                "log_loss_worsened_count": 0,
                "log_loss_tied_count": 0,
                "best_prediction_brier": None,
                "worst_prediction_brier": None,
                "best_prediction_log_loss": None,
                "worst_prediction_log_loss": None,
            }

        row = conn.execute(
            """
            SELECT
                AVG(prediction_brier) as average_prediction_brier,
                AVG(baseline_brier) as average_baseline_brier,
                AVG(brier_delta) as average_brier_delta,
                AVG(prediction_log_loss) as average_prediction_log_loss,
                AVG(baseline_log_loss) as average_baseline_log_loss,
                AVG(log_loss_delta) as average_log_loss_delta,
                SUM(CASE WHEN brier_delta < 0 THEN 1 ELSE 0 END) as brier_improved_count,
                SUM(CASE WHEN brier_delta > 0 THEN 1 ELSE 0 END) as brier_worsened_count,
                SUM(CASE WHEN brier_delta = 0 THEN 1 ELSE 0 END) as brier_tied_count,
                SUM(CASE WHEN log_loss_delta < 0 THEN 1 ELSE 0 END) as log_loss_improved_count,
                SUM(CASE WHEN log_loss_delta > 0 THEN 1 ELSE 0 END) as log_loss_worsened_count,
                SUM(CASE WHEN log_loss_delta = 0 THEN 1 ELSE 0 END) as log_loss_tied_count,
                MIN(prediction_brier) as best_prediction_brier,
                MAX(prediction_brier) as worst_prediction_brier,
                MIN(prediction_log_loss) as best_prediction_log_loss,
                MAX(prediction_log_loss) as worst_prediction_log_loss
            FROM predictions
            WHERE scored_at IS NOT NULL
            """
        ).fetchone()

        return {
            "scored_count": scored_count,
            "average_prediction_brier": row[0],
            "average_baseline_brier": row[1],
            "average_brier_delta": row[2],
            "average_prediction_log_loss": row[3],
            "average_baseline_log_loss": row[4],
            "average_log_loss_delta": row[5],
            "brier_improved_count": row[6] or 0,
            "brier_worsened_count": row[7] or 0,
            "brier_tied_count": row[8] or 0,
            "log_loss_improved_count": row[9] or 0,
            "log_loss_worsened_count": row[10] or 0,
            "log_loss_tied_count": row[11] or 0,
            "best_prediction_brier": row[12],
            "worst_prediction_brier": row[13],
            "best_prediction_log_loss": row[14],
            "worst_prediction_log_loss": row[15],
        }
    finally:
        conn.close()


def list_prediction_performance_rows(limit: int = 50) -> list[dict]:
    """Return recent scored predictions with match info, newest scored first.

    Validates that limit is a positive integer.
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(f"limit must be an integer, got {limit!r}")
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit!r}")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                p.id AS prediction_id,
                p.match_id AS match_id,
                m.home_team AS home_team,
                m.away_team AS away_team,
                p.actual_result AS actual_result,
                p.prediction_brier AS prediction_brier,
                p.baseline_brier AS baseline_brier,
                p.brier_delta AS brier_delta,
                p.prediction_log_loss AS prediction_log_loss,
                p.baseline_log_loss AS baseline_log_loss,
                p.log_loss_delta AS log_loss_delta,
                p.scored_at AS scored_at,
                p.created_at AS created_at
            FROM predictions p
            JOIN matches m ON m.id = p.match_id
            WHERE p.scored_at IS NOT NULL
            ORDER BY p.scored_at DESC, p.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def build_prediction_calibration_bins(bin_size: float = 0.1) -> list[dict]:
    """Build a reliability/calibration table across scored predictions using a one-vs-rest method.

    For each scored prediction, generates three rows (home, draw, away probabilities
    vs whether the outcome occurred) and bins them by predicted probability.
    """
    if isinstance(bin_size, bool) or not isinstance(bin_size, (int, float)):
        raise ValueError(f"bin_size must be a number, got {bin_size!r}")
    if not (0.0 < bin_size <= 0.5):
        raise ValueError(f"bin_size must be between 0.0 (exclusive) and 0.5 (inclusive), got {bin_size!r}")

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT home_probability, draw_probability, away_probability, actual_result
            FROM predictions
            WHERE scored_at IS NOT NULL
            """
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    pairs = []
    for r in rows:
        home_p = r["home_probability"]
        draw_p = r["draw_probability"]
        away_p = r["away_probability"]
        actual = r["actual_result"]

        pairs.append((home_p, 1 if actual == "home" else 0))
        pairs.append((draw_p, 1 if actual == "draw" else 0))
        pairs.append((away_p, 1 if actual == "away" else 0))

    num_bins = int(round(1.0 / bin_size))
    bins = {}
    for i in range(num_bins):
        bins[i] = {
            "lower": i * bin_size,
            "probabilities": [],
            "observed": [],
        }

    for p, obs in pairs:
        p_clamped = min(max(p, 0.0), 1.0)
        bin_idx = int(p_clamped / bin_size + 1e-9)
        if bin_idx >= num_bins:
            bin_idx = num_bins - 1
        bins[bin_idx]["probabilities"].append(p_clamped)
        bins[bin_idx]["observed"].append(obs)

    result = []
    for i in range(num_bins):
        probs = bins[i]["probabilities"]
        obs = bins[i]["observed"]
        count = len(probs)
        if count > 0:
            result.append({
                "bin": round(float(bins[i]["lower"]), 5),
                "count": count,
                "average_predicted_probability": sum(probs) / count,
                "actual_hit_rate": sum(obs) / count,
            })

    result.sort(key=lambda x: x["bin"])
    return result


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")

