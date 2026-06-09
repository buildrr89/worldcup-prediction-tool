# Public Repo Readiness Checklist

A pre-flight checklist to run **before** making this repository public. The goal
is to ship something honest, safe, and clearly labelled as personal/experimental
research.

## Secrets & sensitive data

- [ ] Remove any secrets, API keys, or tokens from the code and commit history.
- [ ] Confirm `.gitignore` excludes `.env`, `data/worldcup.db`, `__pycache__/`,
      and `.DS_Store`. *(Already present — verify it has not regressed.)*
- [ ] Confirm the app and docs contain no private research notes.
- [ ] Confirm no API keys or paid/licensed data are included.
- [ ] Confirm no scraped or paywalled content is included.

## License

- [ ] Choose a license (see [`../LICENSE_RECOMMENDATION.md`](../LICENSE_RECOMMENDATION.md)).
- [ ] Add the actual `LICENSE` file.

## Verify it works

- [ ] Verify the README setup steps work from a clean checkout.
- [ ] Verify the tests pass:
      `python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py`.

## Honesty & framing

- [ ] Confirm the disclaimers are present (not betting automation, not financial
      advice, not guaranteed predictions, not a bookmaker-beating machine).
- [ ] Confirm the first public release is clearly labelled as
      **experimental / personal research**.

## Optional / future steps

- [ ] Issue templates — optional, can be added later.
- [ ] Continuous integration (CI) — optional, can be added later.
