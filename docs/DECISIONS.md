# Decision Log

Architectural decisions for this project. Append a new row whenever you make a
structural choice. Do not rewrite history — supersede with a new row instead.

| Date       | Decision | Reason | Status |
|------------|----------|--------|--------|
| 2026-06-09 | Use Python + Streamlit + SQLite as the stack. | Simplest local-first stack that gives a UI and storage with minimal dependencies. | Active |
| 2026-06-09 | Keep the project personal-use and local-first. | It is a private research notebook, not a product; avoids deployment, auth, and compliance overhead. | Active |
| 2026-06-09 | Use manual odds entry before any APIs. | Keeps the tool simple, offline, and free of scraping/paywall issues while the core math is proven. | Active |
| 2026-06-09 | Use bookmaker probabilities as the baseline. | The market is the best available prior; research should only nudge it. | Active |
| 2026-06-09 | Let AI structure research notes, not calculate final predictions. | Keeps the number path deterministic, transparent, and auditable. | Active |
| 2026-06-09 | Avoid scraping protected/paywalled websites. | Legal/ethical boundary and keeps the tool honest. | Active |
| 2026-06-09 | Avoid cloud deployment for the MVP. | Local-first scope; no need for hosting, accounts, or remote infra. | Active |
| 2026-06-09 | Store factor `weight` inside the `factors.note` text (e.g. `[weight=0.5]`) rather than adding a schema column. | The blending math uses weight, but the DB `factors` table has no weight column. Embedding it in the note keeps the saved factor lossless without a schema change (per task constraint: do not alter schema unless absolutely required). | Active |
| 2026-06-09 | Persist a full prediction flow in a single transaction via `save_prediction_flow`, with `create_*` helpers accepting an optional shared connection. | Avoids partial saves (match without prediction) and keeps the write path explicit and standard-library only — no ORM/repository layer. | Active |
| 2026-06-09 | Prepare the repository for a possible future public/open-source release (added README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, LICENSE_RECOMMENDATION, and a public-repo readiness checklist). | Other developers may want to build on it, improve it, and contribute. Note: the actual license is **not chosen yet** — license decision is pending (see `LICENSE_RECOMMENDATION.md`); no `LICENSE` file added until the maintainer decides. | Accepted |
| 2026-06-10 | Connect project to GitHub for version control and future contributor readiness. | Reduce manual handoff labour and allow future developers/agents to continue from the same source of truth. | Accepted |
| 2026-06-10 | Use Football-Data.co.uk CSVs as the first historical/backtesting data source. | They provide free computer-ready football results and betting odds CSV/Excel data suitable for quantitative analysis without scraping. | Accepted |
| 2026-06-10 | License project under MIT. | MIT is permissive, simple, widely understood, and supports broad developer reuse/contribution. | Accepted |
| 2026-06-10 | Persist parsed historical CSV records, not raw uploaded CSV files. | Keeps local storage lean, avoids storing unnecessary uploaded source files, and preserves only structured match/odds/backtest-ready records. | Accepted |
| 2026-06-10 | Make GitHub repository public. | Allow other developers to inspect, fork, build on, and contribute to the project. | Accepted |
| 2026-06-10 | Use synthetic sample CSV data for public demo/testing. | Gives contributors a safe quick-start path without relying on copyrighted, paid, scraped, or real bookmaker data. | Accepted |
| 2026-06-10 | Use GitHub issue templates and label source-of-truth for public collaboration. | Public contributors need structured ways to report bugs, propose data sources, and suggest improvements without violating local-first, licensing, privacy, or betting-disclaimer boundaries. | Accepted |
| 2026-06-10 | Normalize imported historical match dates to ISO-8601 YYYY-MM-DD. | Raw mixed CSV date formats break chronological sorting, dashboard comparisons, and future analytics. | Accepted |
| 2026-06-10 | Keep Streamlit single-entry app but split UI sections into `src/ui` modules. | Preserves simple `streamlit run app.py` workflow while reducing monolithic app complexity and making future contributor work safer. | Accepted |
| 2026-06-10 | Evaluate manual prediction performance against bookmaker baseline using aggregate Brier score, log loss, improvement deltas, and calibration bins. | The tool must honestly show whether user research factors improve or worsen the probabilistic baseline over time. | Accepted |


