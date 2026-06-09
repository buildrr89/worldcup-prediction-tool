# License Recommendation

> **This is not legal advice.** It is an engineering note to help the maintainer
> pick a license before the repository is made public.

## Current status

**Decision Completed:** The project is now licensed under the **MIT License** (see [LICENSE](file:///Users/restolad/Desktop/WORLDCUP/LICENSE)).

## Recommendation & Decision

**MIT** — Chosen for maximum adoption, simplicity, and ease of contributions.
It is short, permissive, widely understood, and the friendliest option for
contributors who want to build on the project with minimal friction.

**Apache-2.0** — Considered but not chosen for now. It is a good alternative if an explicit **patent grant** matters, but this project does not currently need that extra patent-grant complexity.

**GPLv3** — Considered but not chosen. The project owner does not want to force derivative projects to remain open-source (copyleft), so a permissive license (MIT) was preferred over a restrictive copyleft license.

## Quick comparison

| License    | Style      | Patent grant | Forces derivatives open? | Best when… |
|------------|------------|--------------|--------------------------|------------|
| MIT        | Permissive | No           | No                       | You want the simplest, most adopt-friendly option. (Chosen) |
| Apache-2.0 | Permissive | Yes          | No                       | You want a patent grant and clearer contribution terms. |
| GPLv3      | Copyleft   | Yes          | Yes                      | You want all derivatives to remain open-source. |

## TODO

- [x] Choose a license and add a `LICENSE` file before making the repository public.
