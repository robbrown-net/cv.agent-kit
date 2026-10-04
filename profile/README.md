# profile/: the user's fact bank

Everything in this folder except this README and the `*.example.json` files is personal and
gitignored. The agent creates it during onboarding (`docs/onboarding.md`).

## roles.jsonl

One JSON object per line, one line per job held.

| key | type | notes |
|---|---|---|
| `id` | string | `<employer-slug>-<start year>`, e.g. `examplepay-2021` |
| `employer` | string | as it should appear on a CV |
| `title` | string | the real title |
| `start` | `YYYY-MM` | |
| `end` | `YYYY-MM` or `null` | `null` means current |
| `type` | string | `permanent`, `contract`, `interim`, `freelance` |
| `sector` | string | |
| `summary` | string | one or two sentences on the mandate |
| `source` | string[] | where this came from: `linkedin`, `old-cv-2019`, `interview-2026-10-04` |

## achievements.jsonl

One JSON object per line. This is the **only** source of truth for claims. Every figure in a CV
must trace to a record here.

| key | type | notes |
|---|---|---|
| `id` | string | `<employer-slug>-NN`, e.g. `examplepay-03` |
| `employer` | string | matches `roles.jsonl` |
| `period` | string | e.g. `2021-2023` |
| `claim` | string | the achievement in one PAR-shaped sentence |
| `metric` | object or `null` | `{"value": 3, "unit": "GBP m", "kind": "money"}`; kind is `money`, `time`, `count` or `percent` |
| `themes` | string[] | free tags; normalised by `vocab.json` |
| `register` | string[] | any of `exec`, `delivery`, `practitioner` |
| `verified` | `YYYY-MM-DD` | when the user last confirmed it |
| `source` | string[] | provenance |
| `confidence` | string | `high`, `medium` or `low`. Low never ships without asking |

## Generated, never hand-edited

- `themes.md`: controlled tags with achievement ids ranked strongest first, plus indexes by
  employer and register. Used to pick evidence.
- `figures.md`: every claimable number, and any contested ones. A number not in this file does
  not go in a CV.

Regenerate both with `python3 bin/build-indexes.py`. Use `--check` to detect drift.

## Optional data files

- `vocab.json`: merges raw theme tags into a controlled vocabulary (see `vocab.example.json`).
- `contested.json`: figures where sources disagree, and which value wins (see
  `contested.example.json`).

## Other files

- `voice.md`: writing rules, copied from `templates/voice.md` and then tuned.
- `gaps.md`: open questions only the user can answer. The agent reads it before every draft.
- `masters/<archetype>.md` and `masters/<archetype>-CUTS.md`: see `docs/masters.md`.
