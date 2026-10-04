# Voice, structure and styling

Copied into `profile/voice.md` at onboarding and tuned to the user. These defaults come from
many real applications and the failures that went with them. Change a rule if the user wants
it changed, but do not drop one silently.

## Writing mechanics (hard rules)

- **Follow the style switches in `config/user.json`.** By default that means no em or en dashes
  anywhere in prose (restructure the sentence: split it, or use a comma, colon or parentheses)
  and no contractions ("I am", never "I'm"). Proofread for both before calling a draft final.
- **Bullets follow Problem, Action, Result**, even compressed into one sentence. State or imply
  the situation, what the user did, and the measurable outcome, in that order.
- **Quantify with time, money and counts. Prefer absolute numbers to percentages.**
  "Cut approval time from 12 months to 3" beats "cut approval time by 75 per cent". If the bank
  only holds a percentage, look for the underlying absolute figure before using it.
- **One level of formality throughout.** A formal summary followed by chatty bullets reads as if
  two people wrote it.
- **Never inject a keyword the user cannot defend.** If the bank has no evidence for a fashionable
  term the JD uses, leave it out and tell the user why.

## Register: match the seniority of the target role

Picking the wrong register is worse than picking the wrong achievements.

- **Practitioner** (Lead, Manager, Consultant, hands-on roles): show the mechanics. Named
  techniques, tools, team sizes, cadence: the how.
- **Delivery** (Programme or Delivery Manager, Senior Manager): scope, timelines, budgets, teams
  coordinated, risks retired.
- **Executive** (Director, Head of, VP, C-suite): strip the mechanics out. Lead with mandate,
  scale and business outcome. Name the population changed ("2,000 staff across three divisions")
  rather than the practice introduced. Fewer, larger bullets.

Test each bullet: does it sound like the person who ran the change, or the person brought in to
help? For director level and above, the second is a fail.

## Length budget (plan it before drafting)

Two pages fits roughly: one summary paragraph of about 110 words, 5 or 6 competencies, 6 or 7
achievement bullets across 3 themes, 6 to 8 experience entries with 1 or 2 bullets each, then a
one-line Earlier Career list. Write to that budget instead of trimming six times afterwards.

Never meet the page limit by shrinking the font or margins. Cut duplicated claims first (anything
already in the tagline, summary or competencies), then tighten long bullets, then follow the
master's ranked cut list.

## Section order

1. Name
2. Tagline: three segments split by ` | ` (target title | domain | sector)
3. Contact line: email, phone, location, LinkedIn, all as plain text (ATS parsers miss icons)
4. Summary
5. Core Competencies
6. Key Achievements, grouped under three themes chosen for this JD
7. Experience, newest first
8. Earlier Career, one line per role
9. Education & Certifications, or a grey footer line

## The summary formula

About 110 words, in three moves:
1. A duration and scope claim scoped to this JD ("Fifteen years leading operations in regulated
   fintech...").
2. One short war story with a real banked number.
3. A close on the capability the JD is buying.

## Retitling roles

Echo the target title by changing the noun, never the seniority. "Head of Delivery" may become
"Head of Transformation Delivery" if that is what the role really was. It never becomes
"Director".

## Gaps and career breaks

State them plainly and briefly in the Experience section (for example "Career break: caring
responsibilities"). Do not hide them through date tricks: ATS parsers and interviewers both notice.

## ATS hygiene

- Date ranges use an ASCII hyphen with spaces: `Mar 2021 - Present`. Typographic dashes reach the
  PDF text layer as U+2013, and many parsers only split on `-`.
- A role shorter than a year gets months on both ends. Never a bare single year.
- Email appears as literal text.
- Check the PDF text layer reads in visual order (`verify-output.py --pdf` does this).

## Cover letters

Three or four short paragraphs, under a page. Why this company (a specific, checkable reason),
the single achievement that best answers the JD, what the user would do in the first 90 days,
and a close. Same evidence rule and style rules as the CV.

## User-specific notes

(The agent adds the user's own preferences here during onboarding and over time, with a date.)
