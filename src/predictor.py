"""Deterministic predictor / blending math layer for the World Cup tool.

Local-first, standard library only. Pure functions that take the de-vigged
bookmaker baseline (from `src/odds.py`) and a set of research factors, then
produce a final home / draw / away probability.

Guiding principle: **the bookmaker baseline is the anchor; research factors
only nudge it.** Each factor moves a single outcome by a bounded amount, the
result is clamped to a small positive minimum, and the three outcomes are
renormalised to sum to ~1.0. The market belief is the default belief.

This module computes numbers deterministically: same inputs always produce the
same outputs. No randomness, no AI in the number path.
"""

OUTCOMES = ("home", "draw", "away")

# Smallest probability any outcome may hold after factors are applied, so a
# clamped outcome never collapses to exactly zero.
MIN_PROBABILITY = 0.001


def _check_numeric(value, name: str) -> float:
    """Return ``value`` as a float, or raise ValueError if it is not numeric.

    bool is a subclass of int, so reject it explicitly — True/False are never
    valid probabilities or weights.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric, got {value!r}")
    return float(value)


def _validate_baseline(baseline: dict) -> dict:
    """Validate the baseline dict and return its home/draw/away floats."""
    if not isinstance(baseline, dict):
        raise ValueError(f"baseline must be a dict, got {baseline!r}")

    probs = {}
    for outcome in OUTCOMES:
        if outcome not in baseline:
            raise ValueError(f"baseline is missing key {outcome!r}")
        value = _check_numeric(baseline[outcome], f"baseline[{outcome!r}]")
        if value < 0:
            raise ValueError(
                f"baseline[{outcome!r}] must be >= 0, got {value!r}"
            )
        probs[outcome] = value

    total = probs["home"] + probs["draw"] + probs["away"]
    if abs(total - 1.0) > 0.01:
        raise ValueError(
            f"baseline probabilities must sum to ~1.0, got {total!r}"
        )

    return probs


def _validate_factor(factor: dict, index: int) -> dict:
    """Validate a single factor dict and return a normalised copy."""
    if not isinstance(factor, dict):
        raise ValueError(f"factor[{index}] must be a dict, got {factor!r}")

    target = factor.get("target")
    if target not in OUTCOMES:
        raise ValueError(
            f"factor[{index}] target must be one of {OUTCOMES}, got {target!r}"
        )

    direction = factor.get("direction")
    if direction not in ("positive", "negative"):
        raise ValueError(
            f"factor[{index}] direction must be 'positive' or 'negative', "
            f"got {direction!r}"
        )

    magnitude = _check_numeric(factor.get("magnitude"), f"factor[{index}] magnitude")
    if not 0.0 <= magnitude <= 1.0:
        raise ValueError(
            f"factor[{index}] magnitude must be between 0.0 and 1.0, "
            f"got {magnitude!r}"
        )

    weight = _check_numeric(factor.get("weight"), f"factor[{index}] weight")
    if not 0.0 <= weight <= 1.0:
        raise ValueError(
            f"factor[{index}] weight must be between 0.0 and 1.0, got {weight!r}"
        )

    return {
        "target": target,
        "direction": direction,
        "magnitude": magnitude,
        "weight": weight,
        "note": factor.get("note"),
    }


def blend_probabilities(
    baseline: dict,
    factors: "list[dict] | None" = None,
    max_total_shift: float = 0.15,
) -> dict:
    """Blend a bookmaker baseline with research factors into final probabilities.

    Args:
        baseline: A dict with numeric ``home``, ``draw`` and ``away`` keys, each
            >= 0 and summing to approximately 1.0 (e.g. the de-vigged output of
            ``src/odds.py``).
        factors: An optional list of factor dicts. ``None`` is treated as an
            empty list. Each factor may contain:
                target: one of ``home``, ``draw``, ``away``.
                direction: ``positive`` (add) or ``negative`` (subtract).
                magnitude: number from 0.0 to 1.0.
                weight: number from 0.0 to 1.0.
                note: optional free text.
        max_total_shift: The ceiling on a single factor's raw shift, as a
            fraction. Must be numeric and between 0.0 and 0.5 inclusive.

    Returns:
        A dict with:
            home, draw, away — final probabilities (clamped, summing to ~1.0).
            baseline — the original baseline probabilities, preserved.
            applied_factors — structured summaries of each factor, including the
                signed ``shift`` actually applied.
            max_total_shift — the ceiling used.
            explanation — a short plain-English description of what happened.

    Raises:
        ValueError: If the baseline is malformed, ``max_total_shift`` is out of
            range, or any factor is invalid.
    """
    baseline_probs = _validate_baseline(baseline)

    max_total_shift = _check_numeric(max_total_shift, "max_total_shift")
    if not 0.0 <= max_total_shift <= 0.5:
        raise ValueError(
            f"max_total_shift must be between 0.0 and 0.5, got {max_total_shift!r}"
        )

    if factors is None:
        factors = []
    if not isinstance(factors, list):
        raise ValueError(f"factors must be a list or None, got {factors!r}")

    # Start from a copy of the baseline so the original is preserved untouched.
    probs = dict(baseline_probs)
    applied_factors = []

    for index, factor in enumerate(factors):
        clean = _validate_factor(factor, index)

        raw_shift = clean["magnitude"] * clean["weight"] * max_total_shift
        signed_shift = raw_shift if clean["direction"] == "positive" else -raw_shift

        probs[clean["target"]] += signed_shift

        applied_factors.append(
            {
                "target": clean["target"],
                "direction": clean["direction"],
                "magnitude": clean["magnitude"],
                "weight": clean["weight"],
                "shift": signed_shift,
                "note": clean["note"],
            }
        )

    # Clamp each outcome to a small positive minimum, then renormalise so the
    # three outcomes sum to 1.0 again.
    for outcome in OUTCOMES:
        if probs[outcome] < MIN_PROBABILITY:
            probs[outcome] = MIN_PROBABILITY

    total = probs["home"] + probs["draw"] + probs["away"]
    final = {outcome: probs[outcome] / total for outcome in OUTCOMES}

    explanation = (
        f"Started from the bookmaker baseline (home={baseline_probs['home']:.3f}, "
        f"draw={baseline_probs['draw']:.3f}, away={baseline_probs['away']:.3f}), "
        f"nudged it with {len(applied_factors)} research "
        f"factor{'' if len(applied_factors) == 1 else 's'} "
        f"(each capped at a {max_total_shift:.3f} shift), then clamped and "
        f"normalised home/draw/away to sum to 1.0."
    )

    return {
        "home": final["home"],
        "draw": final["draw"],
        "away": final["away"],
        "baseline": dict(baseline_probs),
        "applied_factors": applied_factors,
        "max_total_shift": max_total_shift,
        "explanation": explanation,
    }
