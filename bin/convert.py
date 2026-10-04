#!/usr/bin/env python3
"""Import existing CVs (pdf, docx, doc) as markdown.

Usage:
  bin/convert.py inbox/                    convert every CV found in inbox/
  bin/convert.py inbox/old-cv.pdf cv.docx  convert specific files
  bin/convert.py inbox/ --out-dir imported/

For each input the markdown is written next to the source (same stem, .md)
unless --out-dir is given. Existing files are NEVER overwritten: a target that
already exists is skipped and reported. Source files are never modified.

When one stem exists in several formats (cv.pdf, cv.docx) only the best is
used: pdf, then docx, then doc.

Tools: poppler (pdftotext) and pandoc are used when installed. Otherwise the
bundled pure-JS fallback is used (node engine/import_doc.js; needs npm install).
  doc   needs LibreOffice (soffice) or re-save the file as .docx

Exit codes: 0 all converted or skipped, 1 some failed, 2 usage or missing tool.
Standard library only.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "engine" / "import_doc.js"

RANK = {".pdf": 0, ".docx": 1, ".doc": 2}
THIN_BYTES = 200


def collect(paths):
    """Gather candidate files, one best source per (directory, stem)."""
    found = []
    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            found.extend(f for f in sorted(p.rglob("*")) if f.is_file())
        elif p.is_file():
            found.append(p)
        else:
            print("error: no such file or directory: %s" % p, file=sys.stderr)
            sys.exit(2)
    best = {}
    for f in found:
        ext = f.suffix.lower()
        if ext not in RANK or f.name.startswith(("~$", ".")):
            continue
        key = f.with_suffix("")
        if key not in best or RANK[ext] < RANK[best[key].suffix.lower()]:
            best[key] = f
    return [best[k] for k in sorted(best)]


def require_tools(files):
    """Poppler/pandoc are optional; the node engine is the fallback."""
    exts = {f.suffix.lower() for f in files}
    need_node = (".pdf" in exts and shutil.which("pdftotext") is None) or (
        ".docx" in exts and shutil.which("pandoc") is None)
    if need_node and ".doc" in exts and not soffice_path():
        need_node = True
    if need_node:
        if shutil.which("node") is None:
            print("error: neither poppler/pandoc nor node is installed. Install node "
                  "(then run: npm install).", file=sys.stderr)
            sys.exit(2)
        if not (ENGINE.parent.parent / "node_modules" / "mammoth").is_dir():
            print("error: node packages missing. Run: npm install", file=sys.stderr)
            sys.exit(2)
    if ".doc" in exts and not soffice_path():
        print("error: .doc files need LibreOffice (brew install --cask libreoffice), "
              "or re-save them as .docx and convert those.", file=sys.stderr)
        sys.exit(2)


def soffice_path():
    found = shutil.which("soffice")
    if found:
        return found
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    return mac if Path(mac).exists() else None


def run(cmd, timeout):
    done = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if done.returncode != 0:
        detail = done.stderr.decode("utf-8", "replace").strip()[:200]
        raise RuntimeError("%s failed: %s" % (cmd[0], detail or "exit %d" % done.returncode))
    return done.stdout


def pandoc(src, out):
    run(["pandoc", "-t", "markdown-raw_html", "--wrap=none", str(src), "-o", str(out)], 60)


def engine(src, out):
    """Pure-JS fallback. import_doc.js refuses to overwrite; out is known absent."""
    run(["node", str(ENGINE), str(src), "--out", str(out)], 120)


def to_md(src, out):
    ext = src.suffix.lower()
    if ext == ".pdf" and shutil.which("pdftotext"):
        text = run(["pdftotext", "-layout", str(src), "-"], 60).decode("utf-8", "replace")
        out.write_text(text, encoding="utf-8")
    elif ext == ".docx" and shutil.which("pandoc"):
        pandoc(src, out)
    else:
        engine(src, out)


def convert_one(src, out):
    if src.suffix.lower() != ".doc":
        return to_md(src, out)
    with tempfile.TemporaryDirectory() as td:
        run([soffice_path(), "--headless", "--convert-to", "docx", "--outdir", td, str(src)], 120)
        docx = Path(td) / (src.stem + ".docx")
        if not docx.exists():
            raise RuntimeError("soffice produced no output")
        to_md(docx, out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Convert existing CVs (pdf/docx/doc) to markdown. Never overwrites.",
        epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="files and/or directories (searched recursively)")
    ap.add_argument("--out-dir", type=Path, help="write .md files here instead of beside the source")
    args = ap.parse_args(argv)

    files = collect(args.paths)
    if not files:
        print("No pdf, docx or doc files found in: %s" % ", ".join(args.paths))
        return 0
    todo = []
    counts = {"ok": 0, "thin": 0, "skipped": 0, "failed": 0}
    for src in files:
        folder = args.out_dir if args.out_dir else src.parent
        out = Path(folder) / (src.stem + ".md")
        if out.exists():
            print("SKIP  %s (exists, never overwritten)" % out)
            counts["skipped"] += 1
        else:
            todo.append((src, out))
    require_tools([s for s, _ in todo])
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
    for src, out in todo:
        try:
            convert_one(src, out)
        except Exception as exc:  # noqa: BLE001 - report and carry on
            print("FAIL  %s: %s" % (src, str(exc)[:200]))
            counts["failed"] += 1
            if out.exists() and out.stat().st_size == 0:
                out.unlink()
            continue
        size = out.stat().st_size
        if size < THIN_BYTES:
            print("THIN  %s (%d bytes; scanned image or empty? needs OCR)" % (out, size))
            counts["thin"] += 1
        else:
            print("OK    %s" % out)
            counts["ok"] += 1
    print("done: %s" % ", ".join("%s=%d" % kv for kv in counts.items()))
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
