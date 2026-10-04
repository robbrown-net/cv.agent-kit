// Build a PDF Buffer from a parsed CV document (see cv_parse.js) using pdfmake.
// Mirrors render_docx.js: same page size, margins, sizes and colours. Text is real, selectable text.
// Font: Arimo (SIL OFL, metric-compatible with Arial) embedded from engine/fonts/. Arial itself is not bundled.
const path = require("path");
const pdfmake = require("pdfmake");
const { pageSize, MARGIN } = require("./config");
const { inlineSegments } = require("./cv_parse");

const BLACK = "#000000";
const GREY = "#595959";
const pt = (twips) => twips / 20;

const FONT_DIR = path.join(__dirname, "fonts");
pdfmake.setUrlAccessPolicy(() => false);
pdfmake.setLocalAccessPolicy((p) => path.resolve(p).startsWith(FONT_DIR + path.sep));
pdfmake.setFonts({
  Arimo: {
    normal: path.join(FONT_DIR, "Arimo_400Regular.ttf"),
    bold: path.join(FONT_DIR, "Arimo_700Bold.ttf"),
    italics: path.join(FONT_DIR, "Arimo_400Regular_Italic.ttf"),
    bolditalics: path.join(FONT_DIR, "Arimo_700Bold_Italic.ttf"),
  },
});

async function renderPdf(cv, config = {}) {
  const { name, tagline, contactLine, sections, footer } = cv;
  const PAGE = pageSize(config);
  const contentW = pt(PAGE.width - MARGIN.left - MARGIN.right);

  const base = { fontSize: 10.5, color: BLACK };
  const runs = (text, o = {}) =>
    inlineSegments(text).map((s) => ({ text: s.text, ...(s.bold ? { bold: true } : {}), ...o }));
  const para = (text, o, margin) => ({ text: runs(text, o), margin });

  const content = [];
  content.push({ text: name, bold: true, fontSize: 16, margin: [0, 0, 0, pt(40)] });
  if (tagline) content.push({ text: tagline, italics: true, color: GREY, margin: [0, 0, 0, pt(60)] });
  if (contactLine) content.push({ text: contactLine, fontSize: 9.5, color: GREY, margin: [0, 0, 0, pt(200)] });

  for (const s of sections) {
    // Heading + rule stay with the first item below them (docx keepNext).
    const heading = [
      { text: s.title.toUpperCase(), bold: true, margin: [0, pt(220), 0, pt(4) + 1] },
      { canvas: [{ type: "line", x1: 0, y1: 0, x2: contentW, y2: 0, lineWidth: 0.5, lineColor: BLACK }], margin: [0, 0, 0, pt(100)] },
    ];
    let pendingKeep = heading; // nodes that must stay with the next node
    const items = s.items;
    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      let node, keep = false;
      if (it.type === "role") {
        keep = true;
        node = {
          columns: [
            { width: "*", text: [{ text: it.title, bold: true }, { text: `,  ${it.company}` }] },
            { width: "auto", text: it.dates, italics: true, fontSize: 9.5, color: GREY, alignment: "right" },
          ],
          columnGap: 4,
          margin: [0, pt(160), 0, pt(40)],
        };
      } else if (it.type === "sub") {
        keep = true;
        node = { text: it.text, bold: true, margin: [0, pt(120), 0, pt(40)] };
      } else if (it.type === "bullet") {
        node = {
          columns: [
            { width: pt(convertIn(0.15)), text: "•" },
            { width: "*", text: runs(it.text) },
          ],
          columnGap: 0,
          margin: [pt(convertIn(0.25) - convertIn(0.15)), 0, 0, pt(50)],
        };
      } else {
        node = para(it.text, {}, [0, 0, 0, pt(100)]);
      }
      if (keep) { pendingKeep.push(node); continue; }
      if (pendingKeep.length) { content.push({ stack: [...pendingKeep, node], unbreakable: true }); pendingKeep = []; }
      else content.push(node);
    }
    if (pendingKeep.length) content.push({ stack: pendingKeep, unbreakable: true });
  }
  if (footer) content.push({ text: runs(footer, { fontSize: 9, color: GREY }), margin: [0, pt(160), 0, 0] });

  const author = config.name || name;
  const docDefinition = {
    info: { title: `${author} CV`, author, subject: "CV", creator: author },
    pageSize: { width: pt(PAGE.width), height: pt(PAGE.height) },
    pageMargins: [pt(MARGIN.left), pt(MARGIN.top), pt(MARGIN.right), pt(MARGIN.bottom)],
    defaultStyle: { font: "Arimo", ...base },
    content,
  };
  return pdfmake.createPdf(docDefinition).getBuffer();
}

// twips per inch
function convertIn(inches) { return inches * 1440; }

module.exports = { renderPdf };
