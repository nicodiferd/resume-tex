#!/usr/bin/env python3
"""Check a compiled resume before it is published.

Fails when the PDF is not exactly one page, when its text (or the .tex it
came from) holds a phone number, an em dash, or a banned public claim.

Usage:
    python scripts/check_pdf.py build/resume.pdf --tex build/resume.tex
    python scripts/check_pdf.py build/private/resume.pdf --allow-phone

Needs pdfinfo and pdftotext (poppler).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
EM_DASH = "\u2014"

# Mirrors the "all" and "bblmlp" scopes of nico-hub rules/banned-claims.txt
# (2026-10-15). The hub list is the policy; this copy keeps CI self-contained.
BANNED = [
    (r"splunk[^\n]{0,40}certif", "certification claims are banned"),
    (r"security\+", "certification claims are banned"),
    (r"comptia", "certification claims are banned"),
    (r"finishing\s+(up\s+)?my\s+5th\s+year", "graduated June 2026"),
    (r"zedi\.sneeks\.ai", "use https://zedi.dev"),
    (r"www\.nicolod\.org", "no DNS record; use https://nicolod.org"),
    (r"proxmox\s+cluster", "the homelab is a single node"),
    (r"12\+? ?-?services?", "stale homelab count"),
    (r"kalshi", "the market stays unnamed"),
    (r"polymarket", "the market stays unnamed"),
    (r"\bbet(s|ting)?\b", "no betting language"),
    (r"wager", "no betting language"),
    (r"bankroll", "no betting language"),
    (r"\bkelly\b", "no betting language"),
    (r"\bp&l\b", "no betting language"),
]


def run(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def page_count(pdf: Path) -> int:
    match = re.search(r"^Pages:\s+(\d+)\s*$", run("pdfinfo", str(pdf)), re.M)
    if not match:
        raise SystemExit(f"check_pdf.py: pdfinfo printed no page count for {pdf}")
    return int(match.group(1))


def scan(label: str, text: str, allow_phone: bool) -> list[str]:
    problems = []
    if not allow_phone and PHONE_RE.search(text):
        # Never print the match: the point is to keep the number out of logs too.
        problems.append(f"{label}: contains a phone number")
    if EM_DASH in text:
        problems.append(f"{label}: contains an em dash (U+2014)")
    for pattern, reason in BANNED:
        if re.search(pattern, text, re.I):
            problems.append(f"{label}: matches banned pattern /{pattern}/ ({reason})")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--tex", type=Path, help="also scan the .tex source (catches link targets)")
    parser.add_argument("--allow-phone", action="store_true", help="private builds only")
    args = parser.parse_args(argv)

    problems = []
    pages = page_count(args.pdf)
    if pages != 1:
        problems.append(f"{args.pdf}: {pages} pages, the resume must be exactly one")
    # Collapse whitespace so a phrase wrapped across lines still matches.
    text = run("pdftotext", "-layout", str(args.pdf), "-")
    flat = re.sub(r"\s+", " ", text)
    problems += scan(str(args.pdf), flat, args.allow_phone)
    if args.tex:
        problems += scan(str(args.tex), args.tex.read_text(encoding="utf-8"), args.allow_phone)

    if problems:
        for line in problems:
            print(f"FAIL {line}", file=sys.stderr)
        return 1
    phone = "phone line allowed" if args.allow_phone else "no phone number"
    print(f"ok {args.pdf}: 1 page, {phone}, no em dash, no banned claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
