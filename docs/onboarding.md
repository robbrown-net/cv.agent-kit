# Onboarding script (for the agent)

Goal: in one sitting of about 30 to 45 minutes, go from an empty repo to a user who can paste a
job description and get a verified two-page CV. Work through the steps in order. Save to disk
after every step, so that if the session dies, the next agent resumes where this one stopped
(check which files exist and are non-empty).

Keep the user moving. Ask at most three questions at a time, offer a default for each, and
accept rough answers: tidying is your job.

## Step 0: Welcome and check the machine

- Tell the user what is about to happen: "I will ask about your career, pull facts out of any
  old CVs you have, build a fact bank, and then write a master CV. After that, each new job
  takes a few minutes."
- Run `bin/doctor.sh`. Explain anything missing in plain words with the install command for
  their OS, and ask before running any installer. Required: `python3`, `node`, and
  `npm install` (which brings the bundled engine). LibreOffice, poppler and pandoc are optional.
- Show them `examples/alex-morgan/` in one line, as a picture of where this ends up.

## Step 1: Config

Ask for: full name as it should appear on a CV, email, phone, location, LinkedIn or website
(optional), paper size (A4 or US Letter, default from their location), spelling (UK or US),
page limit (default 2). Then write `config/user.json`, using `config/user.example.json` as the
shape. Leave `targets` for step 5.

## Step 2: Create the profile

```
mkdir -p profile/masters inbox
cp templates/voice.md templates/gaps.md profile/
touch profile/roles.jsonl profile/achievements.jsonl
```

## Step 3: Gather raw material

Ask the user to drop anything they have into `inbox/`: old CVs in any format, a LinkedIn
export (Settings > Data privacy > Get a copy of your data: Positions and Profile), performance
reviews, award write-ups, and any past job descriptions they liked. Then run
`python3 bin/convert.py inbox/`.

If they have nothing, that is fine: skip to step 4 and interview them instead.

## Step 4: Build the bank

**Roles first.** From the material (or by asking), write one line per job to
`profile/roles.jsonl`. Schema: `profile/README.md`. Confirm the dates with the user in a single
table, since old CVs disagree with each other more often than you expect. Anything you cannot
resolve goes into `profile/gaps.md` as an open question.

**Then achievements.** For each role, extract claims and write them to
`profile/achievements.jsonl`. For every claim:

- Push for the absolute number behind any percentage ("40 per cent faster: from what to
  what?"). Time, money and headcount beat percentages.
- Record where it came from in `source` (`old-cv-2019`, `linkedin`, `interview-2026-10-04`).
- Set `confidence`: `high` if the user confirms it today, `medium` if it is only in an old
  document, `low` if the user is unsure. Ask about anything that looks inflated.
- Tag `themes` (free text for now) and `register`: `exec` (mandate, scale, business outcome),
  `delivery` (programmes, teams, timelines) and/or `practitioner` (methods, tools, hands-on).

Interview prompts that unlock good material: "What were you hired to fix?", "What was
different when you left?", "What is the biggest number you were responsible for?", "What would
your old boss say you are best at?", "What went wrong, and what did you do?".

Where two sources disagree, ask which is right, record the answer and the losing value in
`profile/contested.json` (shape: `profile/contested.example.json`), and fix the bank.

Then run `python3 bin/build-indexes.py`. Walk the user through `profile/themes.md` in two or
three sentences ("your strongest themes are X, Y, Z"), and ask whether the tag names match how
they describe themselves. Merge or rename tags in `profile/vocab.json` if they want.

## Step 5: Targets and archetypes

Ask what roles they are going for (titles, seniority, sectors, locations, permanent or
contract) and save that in `config/user.json` under `targets`.

Propose one to three **archetypes**: groups of jobs that buy the same thing (for example
"operations leader", "transformation programme director", "agile coach"). One is enough to
start. Explain that each archetype gets one long master CV, which every tailored CV is cut from.

## Step 6: Voice

Read `profile/voice.md` with the user in summary form, not in full. Ask the three questions
that change its output most:

1. Which register fits your target roles: executive, delivery or practitioner?
2. Any words or phrases you never want to see? (These go into `style.extra_forbidden_strings`.)
3. Anything you must never claim, such as a client you cannot name or a figure under NDA?
   (These go into `never_claim`.)

Edit `profile/voice.md` and `config/user.json` to match.

## Step 7: First master CV

For each archetype, write `profile/masters/<archetype>.md`, following
`docs/cv-markdown-format.md`. Aim for about three pages, so there is room to cut. Use only banked
figures. Then write `<archetype>-CUTS.md`: a ranked cut order to reach the page limit, a
swap-in table keyed by achievement id, and two alternative summaries. `docs/masters.md` explains
the format, and `examples/alex-morgan/profile/masters/` shows a finished pair.

Run `python3 bin/verify-output.py --draft profile/masters/<archetype>.md` and fix what it flags.

## Step 8: First real run

Ask for a live job description and run workflow A from `AGENTS.md` end to end with the user
watching. Finish by telling them the loop: "Paste a job, I draft, you check, you apply, tell me,
and I move the folder."

## Step 9: Version control (optional)

If they want history, explain that `.gitignore` keeps everything personal out of git by
default, which protects a public fork. To version their own data, they should make a **private**
repo and remove the personal-data block from `.gitignore`. Never push personal data to a public
remote.
