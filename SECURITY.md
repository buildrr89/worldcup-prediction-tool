# Security Policy

This is a **local-first** research tool. It runs offline on the owner's machine
and has no server, accounts, or hosted backend. That design reduces the hosted
attack surface, but it does **not** remove all risk — be careful with what you
commit and share.

## Never commit sensitive data

Do not commit any of the following:

- `.env` files or any environment-variable files.
- API keys, tokens, or credentials of any kind.
- The local database (`data/worldcup.db`) or any other generated data files.
- Private research notes, odds data, or scraped data.

The repository's `.gitignore` already excludes `.env`, `data/worldcup.db`,
`__pycache__/`, and `.DS_Store`. Keep it that way.

If the project later integrates any API, the keys must be stored in `.env`
(which is git-ignored) and **never committed**.

## Reporting a vulnerability

- If the report contains **no sensitive details**, you may open a GitHub issue.
- If the report involves anything sensitive (a working exploit, leaked data, or
  private information), do **not** put it in a public issue. Use the private
  contact below instead.

> Security contact: Please use GitHub private vulnerability reporting if available. If it is not enabled, open a public issue only for non-sensitive security hardening suggestions and avoid posting exploit details, secrets, private data, or local database contents.

## Scrub before you post

Before posting issues, logs, or screenshots:

- Remove any API keys, tokens, file paths, or personal information.
- Scrub local data, odds figures, or research notes you do not intend to make
  public.
- Double-check screenshots for anything in the background or window chrome.
