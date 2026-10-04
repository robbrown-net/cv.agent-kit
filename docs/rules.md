# Rules, with reasons

Each rule exists because skipping it once produced a CV that was wrong in a way nobody noticed
until it mattered. The reason is part of the rule: if a situation falls outside the reason, say
so to the user rather than bending the rule quietly.

**R1. Every figure comes from the bank.**
The usual failure is not wholesale invention but a near-miss: 15 weeks becoming 28, "twice
target" becoming "500 per cent", GBP 3m becoming 5m. These look right, survive review, and get
challenged in interview. `verify-output.py --draft` flags any number that is not banked.

**R2. Never copy a figure from another CV.**
Old CVs, including the user's own, carry figures that exist nowhere else and spread from document
to document unchecked. Bank the figure with a source first, or leave it out.

**R3. Facts stated in chat get banked in the same turn.**
Drafting audits every claim against the files. The audit cannot tell an invention from something
the user said last week, so an unbanked fact gets silently stripped from every future CV.

**R4. Read the indexes, not the bank.**
A bank read end to end gets skimmed, and skimming is where invention starts. Use `themes.md` to
choose ids, `figures.md` for numbers, then pull only those records.

**R5. Never invent facts about the job.**
Salary, closing date, location and contract basis are what the listing says, or "not stated".
Never infer a closing date from when a listing was first seen.

**R6. Register beats content.**
A director CV written in practitioner register gets rejected however good the achievements.
See `profile/voice.md`.

**R7. Never add a keyword the user cannot defend.**
A term they have to walk back in interview costs more than the ATS point it won.

**R8. Dates use ASCII hyphens, and short roles get months.**
A real ATS import once dropped the end date of a short contract and lost an education entry
entirely, from a PDF whose text looked perfect. Parsers split ranges on `-`, not on U+2013.

**R9. Check the artefact, not the draft.**
An image-only PDF looks perfect and is unreadable to an ATS. `verify-output.py --pdf` checks the
page count, the text layer, and that the name and email are present as text.

**R10. LibreOffice page count is not Word page count.**
A CV that renders as exactly two pages in LibreOffice can open as three in Word. Leave about
eight lines of clear space at the foot of the last page.

**R11. The user's edits win.**
If they have edited a generated .docx, edit their file. Never regenerate over it: the draft in the
conversation is stale.

**R12. Deterministic folder names.**
`<YYYYMM>-<company>-<title>`, each part lowercased, spaces turned into underscores, every other
non-alphanumeric character dropped, runs of underscores collapsed. Without this, "M&S" or
"PwC UK LLP" splits one role across two folders. If a part comes out empty, ask.

**R13. The folder is the status.**
`pending/`, then `applications/`, then `archive/`. When `role.json` and the folder disagree,
the folder wins.

## Adding a rule

When something goes wrong in a way a rule would have prevented, add it here with the next
number, a one-line rule and the real reason. If a new rule replaces an old one, say which.
