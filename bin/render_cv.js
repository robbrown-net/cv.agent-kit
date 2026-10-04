#!/usr/bin/env node
// Render a CV written in the format described in docs/cv-markdown-format.md to .docx and/or .pdf.
// Usage: node bin/render_cv.js <cv.md> [--out file.docx|file.pdf] [--config config/user.json] [--pdf | --pdf-only]

const fs = require("fs");
const path = require("path");
const { CvError } = require("../engine/errors");
const configLib = require("../engine/config");
const { parse } = require("../engine/cv_parse");
const { renderDocx } = require("../engine/render_docx");

function fail(msg, line) {
  console.error(`render_cv: ${line ? `line ${line}: ` : ""}${msg}`);
  process.exit(1);
}

const USAGE = "usage: node bin/render_cv.js <cv.md> [--out file.docx|file.pdf] [--config config/user.json] [--pdf | --pdf-only]";
const args = process.argv.slice(2);
let input = null, out = null, configPath = null, wantPdf = false, pdfOnly = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--out") out = args[++i];
  else if (args[i] === "--config") configPath = args[++i];
  else if (args[i] === "--pdf") wantPdf = true;
  else if (args[i] === "--pdf-only") { wantPdf = true; pdfOnly = true; }
  else if (args[i].startsWith("--")) fail(`unknown option ${args[i]}`);
  else if (!input) input = args[i];
  else fail(`unexpected argument ${args[i]}`);
}
if (!input) fail(USAGE);
if (!fs.existsSync(input)) fail(`input file not found: ${input}`);
if (!out) out = path.join(path.dirname(input), path.basename(input, path.extname(input)) + ".docx");
// --out may name either file; the other is derived from it.
const stem = out.replace(/\.(docx|pdf)$/i, "");
if (/\.pdf$/i.test(out)) wantPdf = true;
const pdfOut = stem + ".pdf";
out = stem + ".docx";

(async () => {
  try {
    const config = configLib.load(configPath);
    configLib.pageSize(config); // validate config.cv.paper before parsing
    const cv = parse(fs.readFileSync(input, "utf8"), config);
    if (!pdfOnly) {
      fs.writeFileSync(out, await renderDocx(cv, config));
      console.log(`Wrote ${out}`);
    }
    if (wantPdf) {
      const { renderPdf } = require("../engine/render_pdf");
      fs.writeFileSync(pdfOut, await renderPdf(cv, config));
      console.log(`Wrote ${pdfOut}`);
    }
  } catch (e) {
    if (e instanceof CvError) fail(e.message, e.line);
    throw e;
  }
})();
