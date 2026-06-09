# Public Repo Readiness Checklist

A pre-flight checklist to run **before** making this repository public. The goal
is to ship something honest, safe, and clearly labelled as personal/experimental
research.

## Secrets & sensitive data

- [x] Remove any secrets, API keys, or tokens from the code and commit history.
- [x] Confirm `.gitignore` excludes `.env`, `data/worldcup.db`, `__pycache__/`,
      and `.DS_Store`. *(Already present — verified it has not regressed.)*
- [x] Confirm the app and docs contain no private research notes.
- [x] Confirm no API keys or paid/licensed data are included.
- [x] Confirm no scraped or paywalled content is included.

## License

- [x] Choose a license (see [`../LICENSE_RECOMMENDATION.md`](../LICENSE_RECOMMENDATION.md)).
- [x] Add the actual `LICENSE` file.

## Verify it works

- [x] Verify the README setup steps work from a clean checkout.
- [x] Verify the tests pass:
      `python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py`.

## Honesty & framing

- [x] Confirm the disclaimers are present (not betting automation, not financial
      advice, not guaranteed predictions, not a bookmaker-beating machine).
- [x] Confirm the first public release is clearly labelled as
      **experimental / personal research**.

## Optional / future steps

- [ ] Issue templates — optional, can be added later.
- [ ] Continuous integration (CI) — optional, can be added later.
