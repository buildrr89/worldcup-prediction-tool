# License Recommendation

> **This is not legal advice.** It is an engineering note to help the maintainer
> pick a license before the repository is made public.

## Current status

**No license has been chosen for this project yet.** While no `LICENSE` file is
present, default copyright applies: others may *view* the code but may **not**
freely use, modify, or distribute it. A license must be added before the repo is
useful to other developers.

## Recommendation

**MIT** — recommended default, if the goal is maximum adoption and simplicity.
It is short, permissive, widely understood, and the friendliest option for
contributors who want to build on the project with minimal friction.

**Apache-2.0** — a good alternative if an explicit **patent grant** matters to
you. It is also permissive but adds an express patent license and clearer terms
around contributions and trademarks, at the cost of being longer and slightly
more involved than MIT.

**GPLv3** — only choose this if you specifically want to **force derivatives to
stay open-source** (copyleft). It requires anyone who distributes a modified
version to also release their source under the GPL. Do not pick this unless that
"derivatives must remain open" outcome is an explicit goal.

## Quick comparison

| License    | Style      | Patent grant | Forces derivatives open? | Best when… |
|------------|------------|--------------|--------------------------|------------|
| MIT        | Permissive | No           | No                       | You want the simplest, most adopt-friendly option. |
| Apache-2.0 | Permissive | Yes          | No                       | You want a patent grant and clearer contribution terms. |
| GPLv3      | Copyleft   | Yes          | Yes                      | You want all derivatives to remain open-source. |

## TODO

> **Before making repo public, choose a license and add a `LICENSE` file.**

Until then, the README and `docs/DECISIONS.md` note that the license decision is
pending.
