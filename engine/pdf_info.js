#!/usr/bin/env node
'use strict';
// Page count and text layer of a PDF, pure JS (pdfjs-dist). Approximates `pdftotext -layout`.
// Usage: node engine/pdf_info.js <file.pdf> [--json]
const fs = require('fs');
const path = require('path');

async function pdfInfo(file) {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const data = new Uint8Array(fs.readFileSync(file));
  const doc = await pdfjs.getDocument({ data, useSystemFonts: true, verbosity: 0 }).promise;
  const pageTexts = [];
  for (let n = 1; n <= doc.numPages; n++) {
    const page = await doc.getPage(n);
    const content = await page.getTextContent();
    const items = content.items
      .filter((i) => typeof i.str === 'string')
      .map((i) => ({ s: i.str, x: i.transform[4], y: i.transform[5], w: i.width || 0, h: Math.abs(i.height || i.transform[3] || 10) }));
    // group into lines by y (tolerance: a third of the glyph height)
    items.sort((a, b) => b.y - a.y || a.x - b.x);
    const lines = [];
    for (const it of items) {
      const last = lines[lines.length - 1];
      if (last && Math.abs(last.y - it.y) <= Math.max(2, it.h / 3)) last.items.push(it);
      else lines.push({ y: it.y, items: [it] });
    }
    const out = [];
    for (const ln of lines) {
      ln.items.sort((a, b) => a.x - b.x);
      let text = '';
      let endX = null;
      for (const it of ln.items) {
        if (endX !== null && it.s !== '') {
          const gap = it.x - endX;
          const cw = it.h * 0.5;
          if (gap > cw * 1.5) text += ' '.repeat(Math.min(Math.round(gap / cw), 12));
          else if (gap > cw * 0.2 && !text.endsWith(' ') && !it.s.startsWith(' ')) text += ' ';
        }
        text += it.s;
        endX = it.x + it.w;
      }
      out.push(text.replace(/\s+$/, ''));
    }
    pageTexts.push(out.join('\n'));
    page.cleanup();
  }
  const numPages = doc.numPages;
  try { await doc.destroy(); } catch (_) {}
  const text = pageTexts.join('\f');
  return { pages: numPages, text, chars: text.replace(/\s+/g, '').length };
}

module.exports = { pdfInfo };

if (require.main === module) {
  const args = process.argv.slice(2);
  const json = args.includes('--json');
  const file = args.find((a) => !a.startsWith('--'));
  if (!file) { console.error('usage: node engine/pdf_info.js <file.pdf> [--json]'); process.exit(2); }
  if (!fs.existsSync(file)) { console.error('error: no such file: ' + file); process.exit(2); }
  pdfInfo(path.resolve(file)).then((r) => {
    if (json) console.log(JSON.stringify(r));
    else { console.log('Pages: ' + r.pages); console.log(r.text); }
  }).catch((e) => { console.error('error: could not read PDF: ' + e.message); process.exit(1); });
}
