"""Odds de-vig math layer for the World Cup prediction research tool.

Local-first, standard library only. Pure functions that convert bookmaker
decimal odds into a de-vigged baseline probability for each 1X2 outcome
(home / draw / away).

The "vig" (or overround) is the bookmaker's margin: the raw implied
probabilities from decimal odds sum to *more* than 1.0. De-vigging removes
that margin by normalising each raw probability by their total, producing a
baseline that sums to ~1.0. This baseline is the anchor the rest of the
prediction pipeline nudges — it is never invented by an AI.

This module computes numbers deterministically: same inputs always produce
the same outputs.
"""


def decimal_odds_to_implied_probabilities(
    home_odds: float, draw_odds: float, away_odds: float
) -> dict:
    """Convert 1X2 decimal odds into de-vigged implied probabilities.

    Args:
        home_odds: Decimal odds for the home win (must be > 1.0).
        draw_odds: Decimal odds for the draw (must be > 1.0).
        away_odds: Decimal odds for the away win (must be > 1.0).

    Returns:
        A dict with:
            raw_home, raw_draw, raw_away — raw implied probabilities (1 / odds),
                which include the bookmaker margin.
            overround — sum of the raw implied probabilities (>= ~1.0).
            margin — the bookmaker margin, i.e. ``overround - 1.0``.
            home, draw, away — de-vigged probabilities (each raw value divided
                by the overround). These sum to approximately 1.0.

    Raises:
        ValueError: If any odd is non-numeric or not strictly greater than 1.0.
    """
    odds = {"home": home_odds, "draw": draw_odds, "away": away_odds}

    for name, value in odds.items():
        # Reject non-numeric values. bool is a subclass of int, so exclude it
        # explicitly — True/False are never valid odds.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}_odds must be numeric, got {value!r}")
        if value <= 1.0:
            raise ValueError(
                f"{name}_odds must be greater than 1.0, got {value!r}"
            )

    raw_home = 1.0 / home_odds
    raw_draw = 1.0 / draw_odds
    raw_away = 1.0 / away_odds

    overround = raw_home + raw_draw + raw_away
    margin = overround - 1.0

    return {
        "raw_home": raw_home,
        "raw_draw": raw_draw,
        "raw_away": raw_away,
        "overround": overround,
        "margin": margin,
        "home": raw_home / overround,
        "draw": raw_draw / overround,
        "away": raw_away / overround,
    }
