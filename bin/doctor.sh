#!/usr/bin/env bash
# Checks the tools the kit uses. Read-only: installs nothing.
# Required: python3, node, node_modules (docx, pdfmake, pdfjs-dist, mammoth).
# Optional: LibreOffice, poppler, pandoc (the node engine is the fallback).
cd "$(dirname "$0")/.." || exit 1
ok=0
req() { # name, command, note
  if command -v "$2" >/dev/null 2>&1; then printf '  ok       %-12s %s\n' "$1" "$3"
  else printf '  MISSING  %-12s %s\n' "$1" "$3"; ok=1; fi
}
opt() { # name, present(0/1), note
  if [ "$2" = 0 ]; then printf '  ok       %-12s %s\n' "$1" "$3 (optional)"
  else printf '  optional %-12s %s\n' "$1" "not installed; engine fallback in use ($3)"; fi
}
echo "cv-agent-kit doctor"
req python3 python3 "required: scripts"
req node    node    "required: builds .docx/.pdf"
for p in docx pdfmake pdfjs-dist mammoth; do
  if [ -d "node_modules/$p" ]; then printf '  ok       %-12s %s\n' "$p" "npm package"
  else printf '  MISSING  %-12s %s\n' "$p" "run: npm install"; ok=1; fi
done
if command -v soffice >/dev/null 2>&1 || [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ]; then lo=0; else lo=1; fi
opt LibreOffice $lo "PDF export, old .doc files"
command -v pdftotext >/dev/null 2>&1; opt poppler $? "PDF checks and import"
command -v pandoc >/dev/null 2>&1; opt pandoc $? "importing .docx"
[ -f config/user.json ] && echo "  config/user.json present" || echo "  config/user.json missing: run onboarding (docs/onboarding.md)"
exit $ok
