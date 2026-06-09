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
