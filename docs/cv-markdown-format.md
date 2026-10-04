# CV markdown format

Every CV is written as markdown in this exact shape. `bin/render_cv.js` turns it into a .docx,
and `bin/verify-output.py` checks it. Keep to the shape: the renderer parses headings, not prose.

```markdown
# Alex Morgan
*Head of Operations | Fintech | Scale-ups*
alex.morgan@example.com | +44 7700 900000 | London, UK | linkedin.com/in/alex-morgan-example

## Summary
One paragraph, about 110 words.

## Core Competencies
- Operating model design
- Five or six items in total

## Key Achievements
### Scaling operations
- Problem, action and result in one sentence, with a real number.

## Experience
### Head of Operations | Example Payments Ltd | Mar 2021 - Present
- One or two bullets.

## Earlier Career
- Operations Analyst, Example Bank (Sep 2012 - Feb 2015)

## Education & Certifications
- BSc Economics, University of Example (2008 - 2011)
```

Rules the renderer relies on:

- Line 1 is `# Name`. Line 2 is the italic tagline. Line 3 is the contact line, separated by ` | `.
  If line 3 is missing, the renderer builds it from `config/user.json`.
- `## ` starts a section. Section names are free text, rendered uppercase with a rule beneath.
- Inside `## Experience`, each role is `### Title | Company | Start - End`. Dates use an ASCII
  hyphen with spaces around it (ATS parsers split ranges on `-`, not on en dashes).
- Inside other sections, `### ` is a sub-heading (for example an achievement theme).
- `- ` is a bullet. `**bold**` is supported inline. Any other line is a paragraph.
- A final line starting `> ` is rendered as a small grey footer (certifications, languages).
