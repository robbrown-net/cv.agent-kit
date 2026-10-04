# Masters and CUTS files

Speed comes from never starting a CV from a blank page. Each **archetype** (a family of jobs that
buy the same thing) has one master CV and one CUTS file in `profile/masters/`.

## The master: `<archetype>.md`

- About three pages, deliberately too long, so a tailored CV is made by cutting rather than
  writing.
- Follows `docs/cv-markdown-format.md` exactly.
- Every figure is in the bank. Run `verify-output.py --draft` on it whenever it changes.
- Never sent to anyone as it stands.

## The CUTS file: `<archetype>-CUTS.md`

Three sections:

1. **Ranked cut order.** A numbered list, cheapest cut first ("1. Drop the third Northwind bullet
   ... 2. Collapse Contoso to one line ..."). Cutting to the page limit means working top down.
   Do not invent your own cuts while ranked items remain.
2. **Swap-in table.** `| JD emphasises | swap out | swap in (achievement id) |`. Use it when the JD
   stresses something the master underplays.
3. **Summary variants.** Two alternative summaries written in advance, for example one
   commercial and one people-focused.

## Choosing the archetype

Pick from what the JD is **buying**, its outcomes and requirements, not from words in the
title. A "Head of Transformation" that really wants someone to stand up a PMO is a delivery
archetype. If no master fits, tell the user and offer to create a new archetype. That takes about
ten minutes with the bank in place.

## When the bank changes

If a master and the bank disagree, the bank wins. Fix the master, and note the change at the foot
of the CUTS file.

See `examples/alex-morgan/profile/masters/` for a finished pair.
