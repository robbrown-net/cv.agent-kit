// Parse a CV in the format described in docs/cv-markdown-format.md.
// parse(mdText, config) -> { name, tagline, contactLine, sections: [{title, items}], footer }
// item types: role {title, company, dates} | sub {text} | bullet {text} | para {text}
// Throws CvError (with .line) on format errors.
const { CvError } = require("./errors");

function parse(mdText, config = {}) {
  const fail = (msg, line) => { throw new CvError(msg, line); };
  const lines = mdText.replace(/^﻿/, "").split(/\r?\n/);
  let idx = 0;
  const skipBlank = () => { while (idx < lines.length && lines[idx].trim() === "") idx++; };

  skipBlank();
  if (idx >= lines.length || !/^# (?!#)/.test(lines[idx])) fail("first line must be '# Name'", idx + 1);
  const name = lines[idx].slice(2).trim();
  if (!name) fail("name is empty", idx + 1);
  idx++;

  skipBlank();
  let tagline = "";
  if (idx < lines.length && /^\*(?!\*).*\*\s*$/.test(lines[idx].trim())) {
    tagline = lines[idx].trim().replace(/^\*|\*$/g, "").trim();
    idx++;
  } else if (config.default_tagline) {
    tagline = config.default_tagline;
  }

  skipBlank();
  let contactLine = "";
  if (idx < lines.length && !/^(#|- |> )/.test(lines[idx])) {
    contactLine = lines[idx].trim();
    idx++;
  }
  if (!contactLine && config.contact) {
    const c = config.contact;
    contactLine = [c.email, c.phone, c.location, c.website, c.linkedin].filter(Boolean).join(" | ");
  }

  const sections = [];
  let cur = null, footer = null;
  for (; idx < lines.length; idx++) {
    const raw = lines[idx], ln = idx + 1, t = raw.trim();
    if (t === "") continue;
    if (/^# (?!#)/.test(raw)) fail("only one '# Name' heading is allowed", ln);
    if (/^## /.test(raw)) {
      const title = t.slice(3).trim();
      if (!title) fail("empty section heading", ln);
      cur = { title, items: [] };
      sections.push(cur);
      continue;
    }
    if (/^#{4,}\s/.test(raw)) fail("heading deeper than '###' is not supported", ln);
    if (/^### /.test(raw)) {
      if (!cur) fail("'###' heading before any '##' section", ln);
      const text = t.slice(4).trim();
      if (!text) fail("empty '###' heading", ln);
      if (/^experience$/i.test(cur.title)) {
        const parts = text.split("|").map((s) => s.trim());
        if (parts.length !== 3 || parts.some((p) => !p)) {
          fail(`Experience role heading must be 'Title | Company | Start - End' (3 non-empty pipe-separated parts), got: ${t}`, ln);
        }
        cur.items.push({ type: "role", title: parts[0], company: parts[1], dates: parts[2] });
      } else {
        cur.items.push({ type: "sub", text });
      }
      continue;
    }
    if (/^#/.test(raw) && /^#+\s/.test(raw) === false && /^#+/.test(raw)) {
      fail("malformed heading (missing space after #)", ln);
    }
    if (/^> /.test(raw)) { footer = t.slice(2).trim(); continue; }
    if (/^[-*] /.test(raw)) {
      if (!cur) fail("bullet before any '##' section", ln);
      cur.items.push({ type: "bullet", text: t.slice(2).trim() });
      continue;
    }
    if (!cur) fail(`unexpected text before the first '##' section: ${t}`, ln);
    cur.items.push({ type: "para", text: t });
  }
  if (!sections.length) fail("no '##' sections found");
  if (/\*\*[^*]*$/.test(lines.join("\n").replace(/\*\*[^*\n]*\*\*/g, ""))) {
    for (let i = 0; i < lines.length; i++) {
      const stripped = lines[i].replace(/\*\*[^*]*\*\*/g, "");
      if (stripped.includes("**")) fail("unbalanced ** bold marker", i + 1);
    }
  }
  return { name, tagline, contactLine, sections, footer };
}

// Split text into [{text, bold}] segments on **bold** markers (shared by renderers).
function inlineSegments(text) {
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((p) =>
    /^\*\*[^*]+\*\*$/.test(p) ? { text: p.slice(2, -2), bold: true } : { text: p, bold: false });
}

module.exports = { parse, inlineSegments };
