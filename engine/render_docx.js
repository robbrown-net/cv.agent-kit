// Build a .docx Buffer from a parsed CV document (see cv_parse.js).
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat,
  TabStopType, convertInchesToTwip,
} = require("docx");
const { pageSize, MARGIN } = require("./config");
const { inlineSegments } = require("./cv_parse");

const BLACK = "000000";
const GREY = "595959";

async function renderDocx(cv, config = {}) {
  const { name, tagline, contactLine, sections, footer } = cv;
  const FONT = (config.cv && config.cv.font) || "Arial";
  const PAGE = pageSize(config);

  const run = (text, o = {}) => new TextRun({ text, size: 21, color: BLACK, font: FONT, ...o });
  const inline = (text, o = {}) =>
    inlineSegments(text).map((s) => (s.bold ? run(s.text, { ...o, bold: true }) : run(s.text, o)));

  const RIGHT = PAGE.width - MARGIN.left - MARGIN.right;
  const children = [];

  children.push(new Paragraph({ spacing: { after: 40 }, children: [run(name, { bold: true, size: 32 })] }));
  if (tagline) children.push(new Paragraph({ spacing: { after: 60 }, children: [run(tagline, { italics: true, color: GREY })] }));
  if (contactLine) children.push(new Paragraph({ spacing: { after: 200 }, children: [run(contactLine, { size: 19, color: GREY })] }));

  for (const s of sections) {
    children.push(new Paragraph({
      keepNext: true,
      spacing: { before: 220, after: 100 },
      children: [run(s.title.toUpperCase(), { bold: true })],
      border: { bottom: { color: BLACK, space: 4, style: "single", size: 4 } },
    }));
    for (const it of s.items) {
      if (it.type === "role") {
        children.push(new Paragraph({
          keepNext: true,
          spacing: { before: 160, after: 40 },
          tabStops: [{ type: TabStopType.RIGHT, position: RIGHT }],
          children: [
            run(it.title, { bold: true }),
            run(`,  ${it.company}`),
            run("\t"),
            run(it.dates, { italics: true, size: 19, color: GREY }),
          ],
        }));
      } else if (it.type === "sub") {
        children.push(new Paragraph({ keepNext: true, spacing: { before: 120, after: 40 }, children: [run(it.text, { bold: true })] }));
      } else if (it.type === "bullet") {
        children.push(new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          spacing: { after: 50 },
          children: inline(it.text),
        }));
      } else {
        children.push(new Paragraph({ spacing: { after: 100 }, children: inline(it.text) }));
      }
    }
  }
  if (footer) children.push(new Paragraph({ spacing: { before: 160 }, children: inline(footer, { size: 18, color: GREY }) }));

  const author = config.name || name;
  const doc = new Document({
    creator: author,
    lastModifiedBy: author,
    title: `${author} CV`,
    subject: "CV",
    styles: { default: { document: { run: { font: FONT, size: 21 } } } },
    numbering: {
      config: [{
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: convertInchesToTwip(0.25), hanging: convertInchesToTwip(0.15) } } },
        }],
      }],
    },
    sections: [{
      properties: { page: { size: PAGE, margin: { ...MARGIN } } },
      children,
    }],
  });
  return Packer.toBuffer(doc);
}

module.exports = { renderDocx };
