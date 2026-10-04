#!/usr/bin/env node
'use strict';
// Import an existing CV as text/markdown, pure JS. Never overwrites an existing output.
// Usage: node engine/import_doc.js <file> [--out file.md]   (no --out: print to stdout)
const fs = require('fs');
const path = require('path');

async function docxToMarkdown(file) {
  const mammoth = require('mammoth');
  const r = await mammoth.convertToMarkdown({ path: file });
  return r.value.replace(/\\([.\-()])/g, '$1').replace(/\n{3,}/g, '\n\n').trim() + '\n';
}

async function importDoc(file) {
  const ext = path.extname(file).toLowerCase();
  if (ext === '.docx') return docxToMarkdown(file);
  if (ext === '.pdf') return (await require('./pdf_info').pdfInfo(file)).text.replace(/\f/g, '\n');
  if (ext === '.txt' || ext === '.md') return fs.readFileSync(file, 'utf8');
  if (ext === '.doc') {
    const { spawnSync } = require('child_process');
    const cands = ['soffice', '/Applications/LibreOffice.app/Contents/MacOS/soffice'];
    const os = require('os');
    for (const c of cands) {
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cvdoc-'));
      const r = spawnSync(c, ['--headless', '--convert-to', 'docx', '--outdir', tmp, file], { encoding: 'utf8' });
      const out = path.join(tmp, path.basename(file, path.extname(file)) + '.docx');
      if (!r.error && r.status === 0 && fs.existsSync(out)) return docxToMarkdown(out);
    }
    throw new Error('.doc is an old binary format. Please re-save it as .docx in Word (File > Save As) and try again, or install LibreOffice.');
  }
  throw new Error('unsupported file type "' + ext + '" (use .docx, .pdf, .txt, .md)');
}

module.exports = { importDoc };

if (require.main === module) {
  const args = process.argv.slice(2);
  let out = null; let file = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out') out = args[++i]; else if (!file) file = args[i];
  }
  if (!file || (args.includes('--out') && !out)) { console.error('usage: node engine/import_doc.js <file> [--out file.md]'); process.exit(2); }
  if (!fs.existsSync(file)) { console.error('error: no such file: ' + file); process.exit(2); }
  if (out && fs.existsSync(out)) { console.error('error: ' + out + ' exists; never overwritten'); process.exit(3); }
  importDoc(file).then((text) => {
    if (out) fs.writeFileSync(out, text, { encoding: 'utf8', flag: 'wx' }); else process.stdout.write(text);
  }).catch((e) => { console.error('error: ' + e.message); process.exit(1); });
}
