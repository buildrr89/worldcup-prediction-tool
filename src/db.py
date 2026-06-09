"""SQLite foundation for the World Cup prediction research tool.

Local-first, standard library only. Provides a connection helper and an
`init_db()` that creates the five core tables. Run directly to initialize:

    python src/db.py
"""

import json
import sqlite3
from pathlib import Path

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


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
