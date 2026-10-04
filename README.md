# cv-agent-kit

Fast, accurate, tailored CVs, written by your AI coding agent from a fact bank that you own.

Paste a job description and get a two-page CV tailored to it in a few minutes. Every number on
it traces back to something you have confirmed, and it has been checked for ATS problems before
you see it.

Works with **Claude Code**, **Codex**, **Cursor**, or any agent that reads `AGENTS.md`.

## How it works

1. **Onboarding (about 40 minutes, once).** The agent interviews you, imports your old CVs and
   LinkedIn export, and builds a structured **fact bank**: every role and achievement, with its
   numbers and where they came from.
2. **Masters.** For each kind of job you go for, it writes one long **master CV** and a ranked
   list of cuts.
3. **Each application (minutes).** Paste a job description. The agent picks the right master,
   selects the evidence that answers the job, rewrites the summary, cuts to two pages, then
   verifies the result: no unbanked figures, no forbidden strings, the right page count and a
   readable text layer.

The rule that makes it accurate: **a number that is not in your bank never reaches a CV.**

## Quick start

```bash
git clone https://github.com/robbrown-net/cv.agent-kit.git
cd cv.agent-kit
npm install
```

Then open the folder in your agent and say:

> Set me up.

The agent reads `AGENTS.md`, sees that you are new, and walks you through `docs/onboarding.md`.
You can also download the repo as a .zip and point your agent at the unzipped folder.

### Requirements

Only **Python 3** and **Node.js**. `npm install` fetches everything else into the bundled
`engine/`, which renders .docx and .pdf, counts pages, checks the PDF text layer, and imports
old .docx and .pdf CVs. It needs no system installs and works the same on macOS, Windows and
Linux.

Optional extras are used when present: LibreOffice gives a Word-faithful PDF of the .docx
(`bin/to_pdf.sh`) and imports old .doc files. poppler and pandoc are picked up automatically if
installed. `bin/doctor.sh` shows what you have.

The engine PDF uses Arimo, an open font with the same metrics as Arial (licence in
`engine/fonts/`).

## Your data stays yours

Everything personal (`config/user.json`, `profile/`, `pending/`, `applications/`,
`archive/`, `inbox/`) is in `.gitignore`. A public fork can never leak your CV. To keep your
own history under version control, make a **private** repo and remove that block from
`.gitignore`.

## Layout

```
AGENTS.md            the agent's operating manual (start here if you are an agent)
CLAUDE.md            points Claude Code at AGENTS.md
docs/                onboarding script, CV format, masters, rules
templates/           blank profile files
examples/            a complete fictional user (Alex Morgan) and a sample CV
bin/                 command-line scripts the agent runs
engine/              bundled pure-JS renderer, PDF reader and importer (no system installs)
config/              user.example.json
```

## See an example first

`examples/alex-morgan/` is a fully filled-in fictional profile: roles, achievements, a master,
its cuts, and a tailored CV for a sample job. Try:

```bash
node bin/render_cv.js examples/sample-cv.md --config config/user.example.json --out /tmp/sample.docx --pdf
```

## License

MIT
