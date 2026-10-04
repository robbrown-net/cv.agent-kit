#!/usr/bin/env python3
"""Verify the artefacts of a CV build: the PDF a reader receives, and the
markdown draft behind it.

Three modes:

  --pdf PATH                 check the finished PDF (pages, text layer,
                             required contact details, forbidden strings)
  --draft PATH --bank PATH   check a markdown or plain-text draft against the
                             achievement bank (unverified figures, forbidden
                             strings)
  --selftest                 build throwaway fixtures and prove the checks fire

Standard library only. Nothing here writes to, or otherwise modifies, any file
it inspects. --pdf uses poppler (pdfinfo, pdftotext) when installed, else the node engine (engine/pdf_info.js).

Exit codes: 0 clean, 1 warnings only, 2 errors.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXIT_CLEAN = 0
EXIT_WARNINGS = 1
EXIT_ERRORS = 2

DEFAULT_MAX_PAGES = 2
DEFAULT_MIN_CHARS = 500

APOSTROPHES = "'’ʼ"


# ---------------------------------------------------------------------------
# Forbidden strings
# ---------------------------------------------------------------------------
# Each entry is (label, compiled regex, reason). Extend by adding a tuple: the
# rest of the tool needs no changes. Reasons are printed on failure, so write
# them as a sentence a human can act on.

def _apostrophe_class() -> str:
    return "[" + re.escape(APOSTROPHES) + "]"


def _contraction(word_before: str, word_after: str) -> str:
    return r"\b" + word_before + _apostrophe_class() + word_after + r"\b"


CONTRACTION_RE = re.compile(
    r"\b(?:\w+n" + _apostrophe_class() + r"t"
    r"|(?:I|you|we|they|he|she|it|that|there|what|who|let)" + _apostrophe_class() + r"(?:m|s|ve|re|ll|d)"
    r")\b",
    re.IGNORECASE,
)

DASH_PATTERNS = [
    (
        "em dash",
        re.compile("\u2014"),
        "em dash (U+2014); house style uses a spaced hyphen or a full stop",
    ),
    (
        "en dash",
        re.compile("\u2013"),
        "en dash (U+2013); use a plain hyphen in date ranges",
    ),
    (
        "non-breaking hyphen",
        re.compile("\u2011"),
        "non-breaking hyphen (U+2011); some ATS parsers drop or mangle it",
    ),
]

CONTRACTION_PATTERNS = [
    (
        "contraction",
        CONTRACTION_RE,
        "contractions are too informal for the CV register; write it out in full",
    )
]

ALWAYS_PATTERNS = [
    (
        "bracketed note",
        re.compile(r"\[[^\]]{0,80}\]"),
        "square-bracketed text reads as an unresolved editorial note or an "
        "unfilled placeholder",
    ),
    (
        "parenthetical query",
        re.compile(r"\([^)]*\?\)"),
        "a parenthetical question is an editorial aside that should never ship",
    ),
    (
        "trailing (!)",
        re.compile(r"\(!\)"),
        "an editorial (!) marker survived the draft",
    ),
    ("placeholder", re.compile(r"\bTODO\b", re.IGNORECASE), "unfinished placeholder text"),
    ("placeholder", re.compile(r"\bTBC\b|\bTBD\b", re.IGNORECASE), "unfinished placeholder text"),
    ("placeholder", re.compile(r"\bXX+\b"), "unfinished placeholder text"),
    ("placeholder", re.compile(r"\bLorem\b", re.IGNORECASE), "filler copy left in the document"),
    ("placeholder", re.compile(r"\bINSERT\b", re.IGNORECASE), "unfilled instruction to the writer"),
    ("placeholder", re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE), "unfilled placeholder"),
    (
        "angle-bracket slot",
        re.compile(r"<[A-Za-z_][^<>\n]{0,60}>"),
        "an angle-bracket template slot was never filled in",
    ),
]


def build_forbidden(no_em_dashes=True, no_contractions=True, extra=()):
    """The active forbidden-string list. Driven by config/user.json `style`."""
    patterns = []
    if no_em_dashes:
        patterns += DASH_PATTERNS
    patterns += ALWAYS_PATTERNS
    if no_contractions:
        patterns += CONTRACTION_PATTERNS
    for text in extra or ():
        if text:
            patterns.append(
                ("custom", re.compile(re.escape(str(text)), re.IGNORECASE),
                 "listed in style.extra_forbidden_strings")
            )
    return patterns


FORBIDDEN_PATTERNS = build_forbidden()


class VerificationError(Exception):
    """Raised when an artefact cannot be checked at all."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def normalise_space(text: str) -> str:
    return " ".join(text.split())


def context_around(text: str, start: int, end: int, width: int = 60) -> str:
    """About `width` characters of surrounding text, on one line."""
    half = max(width // 2, 10)
    left = max(0, start - half)
    right = min(len(text), end + half)
    snippet = normalise_space(text[left:right])
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    return prefix + snippet + suffix


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def sentence_around(text: str, start: int, end: int, limit: int = 300) -> str:
    """The sentence (or line) the offset sits in, trimmed to `limit`."""
    boundary = re.compile(r"[.!?\n]")
    left = 0
    for match in boundary.finditer(text, 0, start):
        left = match.end()
    right_match = boundary.search(text, end)
    right = right_match.start() + 1 if right_match else len(text)
    sentence = normalise_space(text[left:right])
    if len(sentence) > limit:
        sentence = sentence[: limit - 3] + "..."
    return sentence


class Report:
    """Collects errors and warnings and decides the exit code."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)

    @property
    def exit_code(self) -> int:
        if self.errors:
            return EXIT_ERRORS
        if self.warnings:
            return EXIT_WARNINGS
        return EXIT_CLEAN

    def emit(self, heading: str, stream=sys.stdout) -> int:
        print(heading, file=stream)
        for note in self.notes:
            print("  note:    " + note, file=stream)
        for warning in self.warnings:
            print("  WARNING: " + warning, file=stream)
        for error in self.errors:
            print("  ERROR:   " + error, file=stream)
        if not self.errors and not self.warnings:
            print("  PASS: no problems found.", file=stream)
        else:
            print(
                "  RESULT: %d error(s), %d warning(s)."
                % (len(self.errors), len(self.warnings)),
                file=stream,
            )
        return self.exit_code


# ---------------------------------------------------------------------------
# Forbidden-string scanning
# ---------------------------------------------------------------------------

def find_forbidden(text: str, patterns=None) -> list[dict]:
    """Every forbidden-string hit in `text`, with context."""
    hits = []
    seen = set()
    for label, pattern, reason in (patterns if patterns is not None else FORBIDDEN_PATTERNS):
        for match in pattern.finditer(text):
            key = (match.start(), match.end(), label)
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                {
                    "label": label,
                    "reason": reason,
                    "text": normalise_space(match.group(0)),
                    "line": line_of(text, match.start()),
                    "context": context_around(text, match.start(), match.end()),
                }
            )
    hits.sort(key=lambda hit: (hit["line"], hit["label"]))
    return hits


def report_forbidden(text: str, report: Report, where: str, patterns=None) -> None:
    for hit in find_forbidden(text, patterns):
        report.error(
            "%s line %d: forbidden %s %r: %s\n           context: %s"
            % (where, hit["line"], hit["label"], hit["text"], hit["reason"], hit["context"])
        )


# ---------------------------------------------------------------------------
# PDF mode
# ---------------------------------------------------------------------------

def run_tool(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise VerificationError(
            "the command %r is not installed. Install poppler-utils "
            "(Debian/Ubuntu: apt install poppler-utils, macOS: brew install poppler)."
            % command[0]
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or (exc.stdout or "").strip() or "command failed"
        raise VerificationError("%s could not read the file: %s" % (command[0], detail))
    return completed.stdout


PAGES_RE = re.compile(r"^Pages:\s+(\d+)\s*$", re.MULTILINE)


def parse_page_count(pdfinfo_output: str) -> int:
    match = PAGES_RE.search(pdfinfo_output)
    if not match:
        raise VerificationError("pdfinfo output carried no 'Pages:' line")
    return int(match.group(1))


ENGINE_PDF_INFO = Path(__file__).resolve().parent.parent / "engine" / "pdf_info.js"


def have_poppler() -> bool:
    return bool(shutil.which("pdfinfo") and shutil.which("pdftotext"))


def have_engine() -> bool:
    return bool(shutil.which("node") and ENGINE_PDF_INFO.is_file()
                and (ENGINE_PDF_INFO.parent.parent / "node_modules" / "pdfjs-dist").is_dir())


def engine_pdf(pdf_path: Path) -> dict:
    """Page count and text via the pure-JS engine (fallback when poppler is absent)."""
    import json as _json
    out = run_tool(["node", str(ENGINE_PDF_INFO), str(pdf_path), "--json"])
    try:
        return _json.loads(out)
    except ValueError as exc:
        raise VerificationError("engine/pdf_info.js gave unreadable output") from exc


def extract_pdf_text(pdf_path: Path) -> str:
    if not have_poppler() and have_engine():
        return engine_pdf(pdf_path)["text"]
    return run_tool(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"])


def verify_pdf(
    pdf_path: Path,
    max_pages: int = DEFAULT_MAX_PAGES,
    min_chars: int = DEFAULT_MIN_CHARS,
    required: tuple[str, ...] = (),
    patterns=None,
) -> Report:
    report = Report()
    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        report.error("no such file: %s" % pdf_path)
        return report
    size = pdf_path.stat().st_size
    if size == 0:
        report.error("file is empty (0 bytes): %s" % pdf_path)
        return report
    report.note("%s, %d bytes" % (pdf_path, size))

    try:
        if not have_poppler() and have_engine():
            pages = int(engine_pdf(pdf_path)["pages"])
        else:
            pages = parse_page_count(run_tool(["pdfinfo", str(pdf_path)]))
    except VerificationError as exc:
        report.error("page count: %s" % exc)
    else:
        if pages > max_pages:
            report.error(
                "page count is %d; the cap is %d. A reader stops at page %d."
                % (pages, max_pages, max_pages)
            )
        else:
            report.note("page count %d (cap %d)" % (pages, max_pages))

    try:
        raw_text = extract_pdf_text(pdf_path)
    except VerificationError as exc:
        report.error("text layer: %s" % exc)
        return report

    flat = normalise_space(raw_text)
    if len(flat) < min_chars:
        report.error(
            "text layer holds %d characters, below the minimum of %d. The page may "
            "look perfect and still be an image: no ATS can read it."
            % (len(flat), min_chars)
        )
    else:
        report.note("text layer %d characters" % len(flat))

    for wanted in required:
        if normalise_space(wanted) not in flat:
            report.error(
                "required string missing from the text layer: %r. If it is visible "
                "on the page, it is carried by an icon, an image or a hyperlink "
                "and an ATS will not see it." % wanted
            )

    report_forbidden(raw_text, report, "text layer", patterns)
    return report


# ---------------------------------------------------------------------------
# Figure extraction
# ---------------------------------------------------------------------------

NUMBER_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")

SCALE_RE = re.compile(r"^\s*(million|billion|thousand|bn|mn|m|k)\b", re.IGNORECASE)
SCALES = {
    "k": 1_000.0,
    "thousand": 1_000.0,
    "m": 1_000_000.0,
    "mn": 1_000_000.0,
    "million": 1_000_000.0,
    "bn": 1_000_000_000.0,
    "billion": 1_000_000_000.0,
}

UNIT_RE = re.compile(
    r"^\s*(%|(?:percent|per\s*cent|percentage\s+points?|pp"
    r"|weeks?|wks?|months?|mths?|years?|yrs?|days?)\b)",
    re.IGNORECASE,
)
DURATION_DAYS = {
    "day": 1.0,
    "days": 1.0,
    "week": 7.0,
    "weeks": 7.0,
    "wk": 7.0,
    "wks": 7.0,
    "month": 30.0,
    "months": 30.0,
    "mth": 30.0,
    "mths": 30.0,
    "year": 365.0,
    "years": 365.0,
    "yr": 365.0,
    "yrs": 365.0,
}

CURRENCY_RE = re.compile(r"(?:[£$€]|\b(?:GBP|USD|EUR)\b)\s*$", re.IGNORECASE)

# Text masked out before figures are extracted, so it never becomes a finding.
MASK_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),                      # e-mail
    re.compile(r"https?://\S+|\bwww\.\S+"),                       # URLs
    re.compile(r"\+?\d[\d()\s.-]{8,}\d"),                         # phone numbers
    re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b"),         # UK postcodes
    re.compile(r"\bpages?\.?\s*\d+\b|\bp\.\s*\d+\b", re.IGNORECASE),   # page refs
    re.compile(                                                    # date ranges
        r"\b(?:19|20)\d{2}\s*(?:-|–|—|to|until)\s*(?:(?:19|20)\d{2}|present|date|now)\b",
        re.IGNORECASE,
    ),
    re.compile(                                                    # month + year
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:19|20)\d{2}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bversion\s*\d+(?:\.\d+)*\b|\bv\d+(?:\.\d+)+\b", re.IGNORECASE),
]


def mask_noise(text: str) -> str:
    """Blank out contact details, dates and similar digits, keeping offsets."""
    masked = list(text)
    for pattern in MASK_PATTERNS:
        for match in pattern.finditer(text):
            for index in range(match.start(), match.end()):
                if masked[index] != "\n":
                    masked[index] = " "
    return "".join(masked)


class Figure:
    """One numeric claim found in a document."""

    def __init__(self, raw, value, kind, days, start, end):
        self.raw = raw
        self.value = value
        self.kind = kind          # "percent", "money", "duration" or "plain"
        self.days = days          # normalised duration in days, else None
        self.start = start
        self.end = end

    def keys(self) -> set:
        """Canonical forms this figure can be matched on."""
        found = {round(self.value, 6)}
        if self.days is not None:
            found.add(("days", round(self.days, 6)))
        return found

    def __repr__(self) -> str:
        return "Figure(%r, %s, %s)" % (self.raw, self.value, self.kind)


def extract_figures(text: str, mask: bool = True, min_bare: float = 10.0) -> list[Figure]:
    """Every numeric claim in `text`.

    `mask` blanks out years, phone numbers, postcodes and page numbers first.
    `min_bare` drops small bare integers with no unit or currency, which are
    almost always counts of teams or people rather than headline claims.
    """
    source = mask_noise(text) if mask else text
    figures: list[Figure] = []

    for match in NUMBER_RE.finditer(source):
        literal = match.group(1)
        try:
            value = float(literal.replace(",", ""))
        except ValueError:
            continue

        start, end = match.start(1), match.end(1)
        before = source[max(0, start - 6):start]
        after = source[end:end + 24]

        has_currency = bool(CURRENCY_RE.search(before))

        scale_match = SCALE_RE.match(after)
        scale_text = ""
        if scale_match:
            scale_text = scale_match.group(1)
            value *= SCALES[scale_text.lower()]
            after = after[scale_match.end():]

        unit_match = UNIT_RE.match(after)
        unit_text = unit_match.group(1).lower().replace(" ", "") if unit_match else ""

        kind = "plain"
        days = None
        if unit_text in ("%", "percent", "percent", "percentagepoint", "percentagepoints", "pp"):
            kind = "percent"
        elif unit_text.rstrip(".") in DURATION_DAYS:
            kind = "duration"
            days = value * DURATION_DAYS[unit_text.rstrip(".")]
        elif has_currency or scale_text.lower() in ("m", "mn", "k", "bn"):
            kind = "money"

        if mask:
            if kind == "plain" and value.is_integer() and 1900 <= value <= 2100:
                continue  # a year that slipped past the mask
            if kind == "plain" and not has_currency and value < min_bare:
                continue  # small bare count, too noisy to flag

        raw_end = end
        if scale_match:
            raw_end += scale_match.end()
        if unit_match:
            raw_end += unit_match.end()
        figures.append(
            Figure(source[start:raw_end].strip(), value, kind, days, start, raw_end)
        )

    return figures


# ---------------------------------------------------------------------------
# Achievement bank
# ---------------------------------------------------------------------------

def load_bank(bank_path: Path) -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    problems: list[str] = []
    text = Path(bank_path).read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            problems.append("bank line %d is not valid JSON: %s" % (number, exc))
            continue
        if not isinstance(record, dict):
            problems.append("bank line %d is not a JSON object" % number)
            continue
        entries.append(record)
    return entries, problems


def bank_keys(entries: list[dict]) -> set:
    """Every figure the bank legitimises, from the metric field and the prose."""
    keys: set = set()
    for record in entries:
        metric = record.get("metric") or {}
        if isinstance(metric, dict):
            value = metric.get("value")
            unit = str(metric.get("unit") or "").lower().strip()
            numeric = None
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric = float(value)
            elif isinstance(value, str):
                for figure in extract_figures(value, mask=False):
                    keys |= figure.keys()
                    numeric = figure.value
            if numeric is not None:
                multiplier = SCALES.get(unit)
                keys.add(round(numeric, 6))
                if multiplier:
                    keys.add(round(numeric * multiplier, 6))
                unit_days = DURATION_DAYS.get(unit.rstrip("s") or unit) or DURATION_DAYS.get(unit)
                if unit_days:
                    keys.add(("days", round(numeric * unit_days, 6)))
        for field in ("claim", "period"):
            prose = record.get(field)
            if isinstance(prose, str):
                for figure in extract_figures(prose, mask=False):
                    keys |= figure.keys()
    return keys


def verify_draft(
    draft_path: Path,
    bank_path: Path,
    min_bare: float = 10.0,
    patterns=None,
) -> Report:
    report = Report()
    draft_path = Path(draft_path)
    bank_path = Path(bank_path)

    if not draft_path.is_file():
        report.error("no such draft: %s" % draft_path)
        return report
    if not bank_path.is_file():
        report.error("no such achievement bank: %s" % bank_path)
        return report

    draft_text = draft_path.read_text(encoding="utf-8", errors="replace")
    if not draft_text.strip():
        report.error("draft is empty: %s" % draft_path)
        return report

    entries, problems = load_bank(bank_path)
    for problem in problems:
        report.error(problem)
    if not entries:
        report.error("achievement bank holds no usable entries: %s" % bank_path)
        return report
    report.note("bank: %d entries from %s" % (len(entries), bank_path))

    permitted = bank_keys(entries)
    figures = extract_figures(draft_text, mask=True, min_bare=min_bare)
    report.note("draft: %d numeric claim(s) examined" % len(figures))

    unverified = 0
    for figure in figures:
        if figure.keys() & permitted:
            continue
        unverified += 1
        report.warn(
            "UNVERIFIED figure %r (line %d, reads as %s): no match in the bank\n"
            "           sentence: %s"
            % (
                figure.raw,
                line_of(draft_text, figure.start),
                figure.kind,
                sentence_around(draft_text, figure.start, figure.end),
            )
        )
    if figures and not unverified:
        report.note("every figure in the draft is backed by the bank")

    report_forbidden(draft_text, report, "draft", patterns)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _pdf_bytes(pages: list[str], with_text: bool = True) -> bytes:
    """A minimal valid PDF. Each entry of `pages` is that page's text."""
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    page_count = len(pages)
    catalog_id = 1
    pages_id = 2
    font_id = 3
    objects.extend([b"", b"", b""])  # reserved slots, filled in below

    kids = []
    for page_text in pages:
        if with_text:
            lines = page_text.split("\n")
            drawn = ["BT", "/F1 11 Tf", "12 TL", "56 760 Td"]
            for line in lines:
                escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
                drawn.append("(%s) Tj T*" % escaped)
            drawn.append("ET")
            stream = "\n".join(drawn).encode("latin-1", "replace")
        else:
            # A filled rectangle only: visually a page, textually nothing.
            stream = b"0.2 0.2 0.2 rg\n56 600 480 160 re f\n"
        content_id = add(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )
        page_id = add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_id, font_id, content_id)
        )
        kids.append(page_id)

    objects[catalog_id - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id
    objects[pages_id - 1] = b"<< /Type /Pages /Count %d /Kids [%s] >>" % (
        page_count,
        b" ".join(b"%d 0 R" % kid for kid in kids),
    )
    objects[font_id - 1] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % index + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog_id,
        xref_at,
    )
    return bytes(out)


CLEAN_BODY = [
    "Alex Morgan",
    "alex.morgan@example.com | +44 7700 900000 | London",
    "",
    "Profile",
    "Operations leader with fifteen years in regulated delivery. I lead teams",
    "through change, hold the standard, and leave the process better than I",
    "found it. Comfortable with ambiguity and with the detail underneath it.",
    "",
    "Experience",
    "Head of Delivery, Acme Co (2019 to 2024)",
    "Cut onboarding time to 15 weeks from a standing start, holding quality.",
    "Delivered a 2m programme to time and to budget across four sites.",
    "Rebuilt the assurance model and doubled throughput against target.",
    "",
    "Delivery Manager, Globex Ltd (2015 to 2019)",
    "Ran a portfolio of thirty projects and reported to the executive board.",
    "Introduced a weekly cadence that held for the whole of the programme.",
]


def _write_fixture(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


BANK_FIXTURE = "\n".join(
    [
        json.dumps(
            {
                "id": "nb-onboarding",
                "employer": "Acme Co",
                "period": "2019-2024",
                "claim": "Cut onboarding time to 15 weeks from a standing start.",
                "metric": {"type": "duration", "value": 15, "unit": "weeks"},
                "themes": ["operations"],
                "register": "plain",
                "confidence": "high",
            }
        ),
        json.dumps(
            {
                "id": "nb-programme",
                "employer": "Acme Co",
                "period": "2019-2024",
                "claim": "Delivered a 2m programme to time and to budget.",
                "metric": {"type": "money", "value": 2, "unit": "m"},
                "themes": ["delivery"],
                "register": "plain",
                "confidence": "high",
            }
        ),
        json.dumps(
            {
                "id": "nb-throughput",
                "employer": "Acme Co",
                "period": "2019-2024",
                "claim": "Doubled throughput against target.",
                "metric": {"type": "ratio", "value": "twice target", "unit": ""},
                "themes": ["delivery"],
                "register": "plain",
                "confidence": "medium",
            }
        ),
        json.dumps(
            {
                "id": "wg-portfolio",
                "employer": "Globex Ltd",
                "period": "2015-2019",
                "claim": "Ran a portfolio of 30 projects reporting to the board.",
                "metric": {"type": "count", "value": 30, "unit": "projects"},
                "themes": ["portfolio"],
                "register": "plain",
                "confidence": "high",
            }
        ),
    ]
)


class SelfTest:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.passed += 1
            print("  PASS  %s" % name)
        else:
            self.failed += 1
            print("  FAIL  %s%s" % (name, ("  (%s)" % detail) if detail else ""))

    def skip(self, name: str, why: str) -> None:
        self.skipped += 1
        print("  SKIP  %s  (%s)" % (name, why))


def run_selftest() -> int:
    print("verify-output selftest")
    test = SelfTest()
    poppler = have_poppler() or have_engine()

    with tempfile.TemporaryDirectory() as raw_dir:
        work = Path(raw_dir)

        # -- PDF cases ---------------------------------------------------
        if not poppler:
            reason = "no PDF reader: install poppler or run npm install; PDF checks skipped"
            for name in (
                "clean PDF passes",
                "3-page PDF fails the page cap",
                "PDF without a text layer fails",
            ):
                test.skip(name, reason)
        else:
            clean_pdf = work / "clean.pdf"
            clean_pdf.write_bytes(_pdf_bytes([ "\n".join(CLEAN_BODY) ]))
            report = verify_pdf(
                clean_pdf,
                max_pages=2,
                min_chars=300,
                required=("Alex Morgan", "alex.morgan@example.com", "+44 7700 900000"),
            )
            test.check(
                "clean PDF passes",
                report.exit_code == EXIT_CLEAN,
                "; ".join(report.errors + report.warnings),
            )

            long_pdf = work / "three-pages.pdf"
            long_pdf.write_bytes(
                _pdf_bytes(["\n".join(CLEAN_BODY), "Continued.", "Continued again."])
            )
            report = verify_pdf(long_pdf, max_pages=2, min_chars=100)
            test.check(
                "3-page PDF fails the page cap",
                report.exit_code == EXIT_ERRORS
                and any("page count is 3" in message for message in report.errors),
                "; ".join(report.errors) or "no error raised",
            )

            image_pdf = work / "no-text.pdf"
            image_pdf.write_bytes(_pdf_bytes(["ignored"], with_text=False))
            report = verify_pdf(image_pdf, max_pages=2, min_chars=300)
            test.check(
                "PDF without a text layer fails",
                report.exit_code == EXIT_ERRORS
                and any("text layer holds" in message for message in report.errors),
                "; ".join(report.errors) or "no error raised",
            )

            empty_pdf = work / "empty.pdf"
            empty_pdf.write_bytes(b"")
            report = verify_pdf(empty_pdf)
            test.check(
                "empty file fails",
                report.exit_code == EXIT_ERRORS,
                "no error raised",
            )

        # -- Draft cases -------------------------------------------------
        bank = _write_fixture(work, "bank.jsonl", BANK_FIXTURE + "\n")
        clean_draft_text = "\n".join(CLEAN_BODY) + "\n"

        clean_draft = _write_fixture(work, "clean.md", clean_draft_text)
        report = verify_draft(clean_draft, bank)
        test.check(
            "draft whose figures are all in the bank passes",
            report.exit_code == EXIT_CLEAN,
            "; ".join(report.errors + report.warnings),
        )

        bang_draft = _write_fixture(
            work, "bang.md", clean_draft_text + "\nWorth thanking(!) the team here.\n"
        )
        report = verify_draft(bang_draft, bank)
        test.check(
            "draft containing thanking(!) fails",
            report.exit_code == EXIT_ERRORS
            and any("(!)" in message for message in report.errors),
            "; ".join(report.errors) or "no error raised",
        )

        dash_draft = _write_fixture(
            work, "dash.md", clean_draft_text + "\nDelivery — on time, every time.\n"
        )
        report = verify_draft(dash_draft, bank)
        test.check(
            "draft containing an em dash fails",
            report.exit_code == EXIT_ERRORS
            and any("em dash" in message for message in report.errors),
            "; ".join(report.errors) or "no error raised",
        )

        hallucination = _write_fixture(
            work,
            "hallucinated.md",
            clean_draft_text + "\nLifted throughput by 500 percent inside 28 weeks.\n",
        )
        report = verify_draft(hallucination, bank)
        flagged = " ".join(report.warnings)
        test.check(
            "500 percent against a bank saying twice target is UNVERIFIED",
            report.exit_code == EXIT_WARNINGS and "500 percent" in flagged,
            flagged or "nothing flagged",
        )
        test.check(
            "28 weeks against a bank saying 15 weeks is UNVERIFIED",
            "28 weeks" in flagged,
            flagged or "nothing flagged",
        )

        placeholder = _write_fixture(
            work, "placeholder.md", clean_draft_text + "\nTODO: add the <ROLE> summary.\n"
        )
        report = verify_draft(placeholder, bank)
        test.check(
            "placeholder text and angle-bracket slots fail",
            report.exit_code == EXIT_ERRORS
            and any("TODO" in message for message in report.errors)
            and any("<ROLE>" in message for message in report.errors),
            "; ".join(report.errors) or "no error raised",
        )

        contraction = _write_fixture(
            work, "contraction.md", clean_draft_text + "\nI'm the person who don't stop.\n"
        )
        report = verify_draft(contraction, bank)
        test.check(
            "contractions fail",
            report.exit_code == EXIT_ERRORS
            and sum("contraction" in message for message in report.errors) >= 2,
            "; ".join(report.errors) or "no error raised",
        )

        equivalences = _write_fixture(
            work,
            "equivalent.md",
            "Delivered a GBP 2m programme. Ran 30 projects over 15 weeks.\n",
        )
        report = verify_draft(equivalences, bank)
        test.check(
            "GBP 2m matches a bank metric of 2 m, and 15 weeks matches 15 weeks",
            report.exit_code == EXIT_CLEAN,
            "; ".join(report.warnings + report.errors),
        )

        noise = _write_fixture(
            work,
            "noise.md",
            "Alex Morgan, alex.morgan@example.com, +44 7700 900000, M1 4BT.\n"
            "Head of Delivery, Acme Co, 2019-2024. See page 2.\n",
        )
        report = verify_draft(noise, bank)
        test.check(
            "years, phone numbers, postcodes and page numbers are ignored",
            report.exit_code == EXIT_CLEAN,
            "; ".join(report.warnings + report.errors),
        )

        # -- Style switches ----------------------------------------------
        dashes = "Delivery — on time. Don't stop. Say banana.\n"
        off = build_forbidden(no_em_dashes=False, no_contractions=False)
        test.check(
            "style switches off: dashes and contractions allowed",
            not any(h["label"] in ("em dash", "contraction") for h in find_forbidden(dashes, off)),
        )
        extra = build_forbidden(no_em_dashes=False, no_contractions=False, extra=["banana"])
        test.check(
            "extra_forbidden_strings fire",
            any(h["label"] == "custom" for h in find_forbidden(dashes, extra)),
        )

    print(
        "\n%d passed, %d failed, %d skipped" % (test.passed, test.failed, test.skipped)
    )
    return EXIT_CLEAN if test.failed == 0 else EXIT_ERRORS


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

EPILOG = """
examples:
  # the last step of a CV build, on the artefact the reader receives
  # (name, email and page cap come from config/user.json)
  bin/verify-output.py --pdf applications/acme/cv.pdf

  # the draft, before it is turned into a .docx (bank defaults to
  # profile/achievements.jsonl)
  bin/verify-output.py --draft applications/acme/cv.md

  # overriding the config
  bin/verify-output.py --pdf cv.pdf --pages 1 --name "Alex Morgan" --require "London"

exit codes:
  0  clean
  1  warnings only (unverified figures)
  2  errors (missing file, page cap, dead text layer, forbidden strings)

what each mode catches:
  --pdf    an empty or missing file, more pages than the cap, a PDF that looks
           right but carries no extractable text (invisible to a human, fatal
           to an ATS), missing contact details, and every forbidden string.
  --draft  numeric claims with no support in the achievement bank, reported as
           UNVERIFIED with the sentence they sit in, plus every forbidden
           string. Near-miss figures are the point: a duration or multiplier
           that drifted from the banked value.

config/user.json keys used: name, contact.email, cv.max_pages,
style.no_em_dashes, style.no_contractions, style.extra_forbidden_strings.

Nothing is ever written to the files being inspected.
"""


def load_config(root: Path) -> dict:
    """config/user.json under `root`, or {} if absent or unreadable."""
    path = Path(root) / "config" / "user.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("warning: could not read %s: %s" % (path, exc), file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify-output.py",
        description=(
            "Verify a CV build: the finished PDF, or a draft against the "
            "achievement bank. Read-only; poppler is needed for --pdf."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        type=Path,
        metavar="DIR",
        help="repo root holding config/ and profile/ (default: parent of bin/)",
    )
    mode = parser.add_argument_group("modes (choose one)")
    mode.add_argument("--pdf", type=Path, metavar="PATH", help="PDF to verify")
    mode.add_argument("--draft", type=Path, metavar="PATH", help="markdown or text draft to verify")
    mode.add_argument("--selftest", action="store_true", help="run the built-in fixtures and exit")

    pdf_opts = parser.add_argument_group("--pdf options")
    pdf_opts.add_argument(
        "--pages", type=int, metavar="N",
        help="maximum page count (default: cv.max_pages from config, else %d)" % DEFAULT_MAX_PAGES,
    )
    pdf_opts.add_argument(
        "--min-chars", type=int, default=DEFAULT_MIN_CHARS, metavar="N",
        help="minimum characters in the text layer (default: %d)" % DEFAULT_MIN_CHARS,
    )
    pdf_opts.add_argument("--name", help="name that must appear (default: name from config)")
    pdf_opts.add_argument("--email", help="e-mail that must appear (default: contact.email from config)")
    pdf_opts.add_argument("--phone", help="phone number that must appear (not defaulted)")
    pdf_opts.add_argument(
        "--require", action="append", default=[], metavar="TEXT",
        help="any other string that must appear; repeatable",
    )

    draft_opts = parser.add_argument_group("--draft options")
    draft_opts.add_argument(
        "--bank", type=Path, metavar="PATH",
        help="achievement bank JSONL (default: <root>/profile/achievements.jsonl)",
    )
    draft_opts.add_argument(
        "--min-bare", type=float, default=10.0, metavar="N",
        help=(
            "ignore bare numbers below this with no unit or currency "
            "(default: 10; set to 0 to check every number, at the cost of noise)"
        ),
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    chosen = [bool(args.pdf), bool(args.draft), bool(args.selftest)]
    if sum(chosen) != 1:
        parser.error("choose exactly one of --pdf, --draft or --selftest")

    if args.selftest:
        return run_selftest()

    root = (args.root or Path(__file__).resolve().parent.parent).resolve()
    config = load_config(root)
    contact = config.get("contact") if isinstance(config.get("contact"), dict) else {}
    cv = config.get("cv") if isinstance(config.get("cv"), dict) else {}
    style = config.get("style") if isinstance(config.get("style"), dict) else {}
    patterns = build_forbidden(
        no_em_dashes=style.get("no_em_dashes", True),
        no_contractions=style.get("no_contractions", True),
        extra=style.get("extra_forbidden_strings") or (),
    )

    if args.pdf:
        name = args.name or config.get("name")
        email = args.email or contact.get("email")
        max_pages = args.pages or cv.get("max_pages") or DEFAULT_MAX_PAGES
        required = [value for value in (name, email, args.phone) if value]
        required.extend(args.require)
        report = verify_pdf(args.pdf, int(max_pages), args.min_chars, tuple(required), patterns)
        return report.emit("PDF check: %s" % args.pdf)

    bank = args.bank or (root / "profile" / "achievements.jsonl")
    report = verify_draft(args.draft, bank, min_bare=args.min_bare, patterns=patterns)
    return report.emit("Draft check: %s" % args.draft)


if __name__ == "__main__":
    sys.exit(main())
