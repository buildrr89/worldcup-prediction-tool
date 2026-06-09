## Summary

Briefly describe the change and its goal.

## Scope

- [ ] Bug fix
- [ ] Documentation update
- [ ] New local baseline feature/importer
- [ ] Test coverage addition
- [ ] Other (please specify)

## Files changed

List the main files modified or created by this pull request.

## Validation commands run

Please run the following validation commands locally and paste the output below:

```bash
# 1. Run all unit tests
python3 -m unittest tests/test_odds.py tests/test_predictor.py tests/test_scoring.py tests/test_db.py tests/test_football_data_csv.py

# 2. Byte-compile to check for syntax errors
python3 -m compileall src app.py
```

Validation output:
```text
# Paste output here
```

## Local-first checklist

- [ ] **No cloud dependencies**: No hosting configuration, no Vercel/Supabase, no third-party auth, no API integrations.
- [ ] **No user accounts or payments**: Kept entirely personal and offline.
- [ ] **No paid, scraped, or protected data**: No copyrighted datasets or paywalled content. Used synthetic/open-licensed data only.
- [ ] **No secrets**: No API keys, credentials, or `.env` files committed.
- [ ] **No database files**: No local SQLite databases (`data/worldcup.db`) or cache files committed.
- [ ] **No betting/prediction guarantees**: Avoided any claim that the tool beats bookmakers or guarantees winnings.

## UI Changes

If this PR changes the Streamlit UI, please attach screenshots or a short recording below:

## Documentation & Decisions

- [ ] Checked and updated `docs/STATUS.md` with completed tasks, next task, and last updated date?
- [ ] Added a row to `docs/DECISIONS.md` if an architectural or structural decision was made?
