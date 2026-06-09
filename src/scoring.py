"""Scoring / evaluation math layer for the World Cup prediction research tool.

Local-first, standard library only. Pure functions that judge a predicted
home / draw / away probability distribution against the actual match outcome,
so the owner can measure whether research factors beat the raw bookmaker
baseline.

Two proper scoring rules are provided:

- **Brier score** — the mean squared error between the predicted probabilities
  and the one-hot actual outcome across the three outcomes. Lower is better; a
  perfect, fully-confident correct prediction scores 0.0.
- **Log loss** — the negative log of the probability assigned to the outcome
  that actually happened. Lower is better; it punishes confident wrong
  predictions heavily.

Both are deterministic: same inputs always produce the same outputs. No
randomness, no AI in the number path. The bookmaker baseline is the anchor the
prediction is compared against.
"""

import math

OUTCOMES = ("home", "draw", "away")


def _check_numeric(value, name: str) -> float:
    """Return ``value`` as a float, or raise ValueError if it is not numeric.

    bool is a subclass of int, so reject it explicitly — True/False are never
    valid probabilities.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric, got {value!r}")
    return float(value)


def validate_probabilities(probabilities: dict) -> dict:
    """Validate a home/draw/away probability dict and return a cleaned copy.

    Args:
        probabilities: A dict with numeric ``home``, ``draw`` and ``away`` keys,
            each between 0.0 and 1.0 inclusive and summing to approximately 1.0.

    Returns:
        A new dict with just the ``home``, ``draw`` and ``away`` float values.

    Raises:
        ValueError: If the input is not a dict, is missing a key, has a
            non-numeric or out-of-range value, or does not sum to ~1.0.
    """
    if not isinstance(probabilities, dict):
        raise ValueError(
            f"probabilities must be a dict, got {probabilities!r}"
        )

    cleaned = {}
    for outcome in OUTCOMES:
        if outcome not in probabilities:
            raise ValueError(f"probabilities is missing key {outcome!r}")
        value = _check_numeric(
            probabilities[outcome], f"probabilities[{outcome!r}]"
        )
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"probabilities[{outcome!r}] must be between 0.0 and 1.0, "
                f"got {value!r}"
            )
        cleaned[outcome] = value

    total = cleaned["home"] + cleaned["draw"] + cleaned["away"]
    if abs(total - 1.0) > 0.01:
        raise ValueError(
            f"probabilities must sum to ~1.0, got {total!r}"
        )

    return cleaned


def actual_result_to_one_hot(actual_result: str) -> dict:
    """Convert an actual outcome label into a one-hot home/draw/away dict.

    Args:
        actual_result: One of ``home``, ``draw`` or ``away``.

    Returns:
        A dict with 1.0 for the outcome that happened and 0.0 for the others.

    Raises:
        ValueError: If ``actual_result`` is not one of the three outcomes.
    """
    if actual_result not in OUTCOMES:
        raise ValueError(
            f"actual_result must be one of {OUTCOMES}, got {actual_result!r}"
        )

    return {outcome: (1.0 if outcome == actual_result else 0.0) for outcome in OUTCOMES}


def brier_score(probabilities: dict, actual_result: str) -> float:
    """Brier score for a 3-outcome football market. Lower is better.

    Computes ``sum((predicted - actual) ** 2)`` across home/draw/away, where
    ``actual`` is the one-hot encoding of the outcome that happened. A perfect,
    fully-confident correct prediction scores 0.0.

    Args:
        probabilities: A validated-able home/draw/away probability dict.
        actual_result: One of ``home``, ``draw`` or ``away``.

    Returns:
        The Brier score as a float.

    Raises:
        ValueError: If the probabilities or actual result are invalid.
    """
    probs = validate_probabilities(probabilities)
    one_hot = actual_result_to_one_hot(actual_result)

    return sum((probs[outcome] - one_hot[outcome]) ** 2 for outcome in OUTCOMES)


def log_loss(probabilities: dict, actual_result: str, epsilon: float = 1e-15) -> float:
    """Log loss for a 3-outcome football market. Lower is better.

    Returns ``-log(p)`` where ``p`` is the probability assigned to the outcome
    that actually happened, clamped to ``[epsilon, 1 - epsilon]`` so a 0.0 or
    1.0 probability never produces an infinite score. A confident correct
    prediction approaches 0.0; a confident wrong prediction produces a large
    penalty.

    Args:
        probabilities: A validated-able home/draw/away probability dict.
        actual_result: One of ``home``, ``draw`` or ``away``.
        epsilon: Small clamp, numeric and between 0.0 and 0.1 inclusive.

    Returns:
        The log loss as a float.

    Raises:
        ValueError: If the probabilities, actual result, or epsilon are invalid.
    """
    probs = validate_probabilities(probabilities)

    epsilon = _check_numeric(epsilon, "epsilon")
    if not 0.0 <= epsilon <= 0.1:
        raise ValueError(
            f"epsilon must be between 0.0 and 0.1, got {epsilon!r}"
        )

    # Select the probability assigned to the outcome that actually happened.
    # actual_result_to_one_hot also validates the label and raises on bad input.
    one_hot = actual_result_to_one_hot(actual_result)
    actual_probability = next(
        probs[outcome] for outcome in OUTCOMES if one_hot[outcome] == 1.0
    )

    clamped = min(max(actual_probability, epsilon), 1.0 - epsilon)
    return -math.log(clamped)


def compare_prediction_to_baseline(
    prediction: dict, baseline: dict, actual_result: str
) -> dict:
    """Score a prediction against the bookmaker baseline for one match.

    Computes the Brier score and log loss for both the prediction and the
    baseline against the same actual outcome, and reports the deltas plus
    whether the prediction improved on the baseline (a lower score is better).

    Args:
        prediction: The blended home/draw/away probability dict.
        baseline: The de-vigged bookmaker home/draw/away probability dict.
        actual_result: One of ``home``, ``draw`` or ``away``.

    Returns:
        A dict with:
            prediction_brier, baseline_brier — Brier scores.
            brier_delta — ``prediction_brier - baseline_brier``.
            prediction_log_loss, baseline_log_loss — log losses.
            log_loss_delta — ``prediction_log_loss - baseline_log_loss``.
            prediction_improved_brier — True if the prediction's Brier score is
                lower than the baseline's.
            prediction_improved_log_loss — True if the prediction's log loss is
                lower than the baseline's.

    Raises:
        ValueError: If any probability dict or the actual result is invalid.
    """
    prediction_brier = brier_score(prediction, actual_result)
    baseline_brier = brier_score(baseline, actual_result)
    prediction_log_loss = log_loss(prediction, actual_result)
    baseline_log_loss = log_loss(baseline, actual_result)

    return {
        "prediction_brier": prediction_brier,
        "baseline_brier": baseline_brier,
        "brier_delta": prediction_brier - baseline_brier,
        "prediction_log_loss": prediction_log_loss,
        "baseline_log_loss": baseline_log_loss,
        "log_loss_delta": prediction_log_loss - baseline_log_loss,
        "prediction_improved_brier": prediction_brier < baseline_brier,
        "prediction_improved_log_loss": prediction_log_loss < baseline_log_loss,
    }
