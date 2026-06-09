"""Football-Data.co.uk CSV importer for historical results and odds backtesting.

Standard library only. Converts CSV row data containing Date, HomeTeam,
AwayTeam, FTR, and bookmaker odds into clean historical match dicts.
Computes baseline probabilities, and provides summary and backtesting evaluation.
"""

import csv
from datetime import datetime
import io
from pathlib import Path
from src.odds import decimal_odds_to_implied_probabilities
from src.scoring import brier_score, log_loss


def parse_result(ftr: str) -> str:
    """Map H, D, A to home, draw, away.

    Strip whitespace, case-insensitive. Raise ValueError for invalid result.
    """
    if not isinstance(ftr, str):
        raise ValueError(f"ftr must be a string, got {ftr!r}")
    
    cleaned = ftr.strip().upper()
    if cleaned == "H":
        return "home"
    elif cleaned == "D":
        return "draw"
    elif cleaned == "A":
        return "away"
    else:
        raise ValueError(f"Invalid FTR value: {ftr!r}")


def parse_float(value: str) -> float | None:
    """Strip whitespace. Return None for empty values.

    Convert valid strings to float. Raise ValueError for invalid non-empty values.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Value cannot be boolean: {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        raise ValueError(f"Value must be a string or number, got {value!r}")
    
    cleaned = value.strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError as e:
        raise ValueError(f"Invalid float: {value!r}") from e


def parse_date(value: str) -> str:
    """Normalize parsed Football-Data CSV dates to ISO-8601 YYYY-MM-DD.

    Strip whitespace. Raise ValueError for blank values or unsupported formats.
    """
    if not isinstance(value, str):
        raise ValueError("Date value must be a string")
    
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Date value cannot be blank")

    formats = [
        "%d/%m/%y",
        "%d/%m/%Y",
        "%d-%m-%y",
        "%d-%m-%Y",
        "%Y-%m-%d"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {value!r}")


def row_to_historical_match(row: dict, odds_prefix: str = "B365") -> dict | None:
    """Convert one Football-Data.co.uk CSV row to a clean dictionary.

    If any required field (Date, HomeTeam, AwayTeam, FTR) or odds fields are missing
    or blank, return None. Use decimal_odds_to_implied_probabilities to calculate
    de-vigged baseline.

    Raise controlled ValueError only when a present value is invalid.
    """
    required_fields = ["Date", "HomeTeam", "AwayTeam", "FTR"]
    odds_fields = [f"{odds_prefix}H", f"{odds_prefix}D", f"{odds_prefix}A"]

    # If any required field is missing/blank, return None
    for field in required_fields:
        if field not in row or row[field] is None:
            return None
        if str(row[field]).strip() == "":
            return None

    # If odds fields are missing/blank, return None
    for field in odds_fields:
        if field not in row or row[field] is None:
            return None
        if str(row[field]).strip() == "":
            return None

    date_raw = str(row["Date"])
    try:
        date_val = parse_date(date_raw)
    except ValueError as e:
        raise ValueError(f"Invalid date: {e}")

    home_val = str(row["HomeTeam"]).strip()
    away_val = str(row["AwayTeam"]).strip()
    ftr_val = str(row["FTR"]).strip()

    try:
        actual_result_val = parse_result(ftr_val)
    except ValueError as e:
        raise ValueError(f"Invalid result: {e}")

    try:
        home_odds = parse_float(row[f"{odds_prefix}H"])
        draw_odds = parse_float(row[f"{odds_prefix}D"])
        away_odds = parse_float(row[f"{odds_prefix}A"])
    except ValueError as e:
        raise ValueError(f"Invalid odds value: {e}")

    if home_odds is None or draw_odds is None or away_odds is None:
        return None

    try:
        baseline_probs = decimal_odds_to_implied_probabilities(
            home_odds, draw_odds, away_odds
        )
    except ValueError as e:
        raise ValueError(f"Invalid odds ranges: {e}")

    return {
        "date": date_val,
        "home_team": home_val,
        "away_team": away_val,
        "actual_result": actual_result_val,
        "home_decimal_odds": home_odds,
        "draw_decimal_odds": draw_odds,
        "away_decimal_odds": away_odds,
        "baseline": {
            "home": baseline_probs["home"],
            "draw": baseline_probs["draw"],
            "away": baseline_probs["away"],
        },
        "margin": baseline_probs["margin"],
        "source": "football-data.co.uk",
        "odds_prefix": odds_prefix,
    }


def load_csv_file(file_obj, odds_prefix: str = "B365") -> list[dict]:
    """Read a CSV from a file-like object or bytes, and return cleaned matches.

    file_obj can be:
    - bytes
    - a file-like object returning bytes (e.g. BytesIO, Streamlit UploadedFile)
    - a text stream/file-like object returning strings (e.g. StringIO, open file)

    Use csv.DictReader. Convert rows with row_to_historical_match. Skip rows
    that return None. Return list of cleaned matches.
    Include row number in error messages when a row has invalid data.
    """
    if isinstance(file_obj, bytes):
        text = file_obj.decode("utf-8-sig")
        f = io.StringIO(text)
    elif hasattr(file_obj, "read"):
        content = file_obj.read()
        if isinstance(content, bytes):
            text = content.decode("utf-8-sig")
        else:
            text = content
        f = io.StringIO(text)
    else:
        # Fallback if it's already an iterable of strings/bytes (like a list of lines)
        lines = []
        for line in file_obj:
            if isinstance(line, bytes):
                lines.append(line.decode("utf-8-sig"))
            else:
                lines.append(line)
        f = lines

    matches = []
    reader = csv.DictReader(f)
    for row in reader:
        line_num = reader.line_num
        try:
            match = row_to_historical_match(row, odds_prefix=odds_prefix)
            if match is not None:
                matches.append(match)
        except ValueError as e:
            raise ValueError(f"Row {line_num}: {e}")
    return matches


def load_csv(path: str | Path, odds_prefix: str = "B365") -> list[dict]:
    """Read a CSV file from disk.

    Use csv.DictReader. Convert rows with row_to_historical_match. Skip rows
    that return None. Return list of cleaned matches.
    Include row number in error messages when a row has invalid data.
    """
    with open(path, mode="r", encoding="utf-8-sig") as f:
        return load_csv_file(f, odds_prefix=odds_prefix)


def summarise_historical_matches(matches: list[dict]) -> dict:
    """Return summary statistics of historical matches.

    average_margin should be 0.0 for empty input.
    """
    match_count = len(matches)
    if match_count == 0:
        return {
            "match_count": 0,
            "home_wins": 0,
            "draws": 0,
            "away_wins": 0,
            "average_margin": 0.0,
        }

    home_wins = sum(1 for m in matches if m["actual_result"] == "home")
    draws = sum(1 for m in matches if m["actual_result"] == "draw")
    away_wins = sum(1 for m in matches if m["actual_result"] == "away")
    average_margin = sum(m["margin"] for m in matches) / match_count

    return {
        "match_count": match_count,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "average_margin": average_margin,
    }


def backtest_baseline(matches: list[dict]) -> dict:
    """Calculate average Brier score and Log Loss for baseline probabilities."""
    match_count = len(matches)
    if match_count == 0:
        return {
            "match_count": 0,
            "average_brier": 0.0,
            "average_log_loss": 0.0,
        }

    total_brier = 0.0
    total_log_loss = 0.0

    for m in matches:
        total_brier += brier_score(m["baseline"], m["actual_result"])
        total_log_loss += log_loss(m["baseline"], m["actual_result"])

    return {
        "match_count": match_count,
        "average_brier": total_brier / match_count,
        "average_log_loss": total_log_loss / match_count,
    }
