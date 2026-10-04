#!/usr/bin/env bash
# Convert a .docx to PDF (same folder) with LibreOffice headless. Usage: bin/to_pdf.sh <file.docx>
set -euo pipefail
[ $# -eq 1 ] && [ -f "$1" ] || { echo "usage: $0 <file.docx>" >&2; exit 1; }
SOFFICE="$(command -v soffice || true)"
[ -z "$SOFFICE" ] && [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ] && SOFFICE=/Applications/LibreOffice.app/Contents/MacOS/soffice
[ -n "$SOFFICE" ] || { echo "LibreOffice (soffice) not found. Install it, or open the .docx in Word and export to PDF." >&2; exit 1; }
DIR="$(cd "$(dirname "$1")" && pwd)"
"$SOFFICE" --headless --convert-to pdf --outdir "$DIR" "$1" >/dev/null
PDF="$DIR/$(basename "${1%.*}").pdf"
[ -f "$PDF" ] || { echo "conversion failed" >&2; exit 1; }
echo "Wrote $PDF"
if command -v pdfinfo >/dev/null; then pdfinfo "$PDF" | grep '^Pages:'; else echo "pdfinfo not found; check page count manually"; fi
