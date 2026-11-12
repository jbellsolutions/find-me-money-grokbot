#!/usr/bin/env python3
"""Turn a PDF into plain text so the bot reads words, not pages of images.

usage: pdf2txt.py file.pdf [--pages 1-5] > file.txt
Order: pdftotext (poppler) if present, else pypdf. Heavy option for scanned/complex
PDFs: docling (not installed by default; ask the owner first, it is large).
"""
import argparse
import shutil
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="")
    a = ap.parse_args()
    first, last = (a.pages.split("-") + [""])[:2] if a.pages else ("", "")
    if shutil.which("pdftotext"):
        cmd = ["pdftotext", "-layout"]
        if first:
            cmd += ["-f", first, "-l", last or first]
        cmd += [a.pdf, "-"]
        sys.stdout.write(subprocess.run(cmd, capture_output=True, text=True).stdout)
        return
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        sys.exit("pdf2txt: neither pdftotext nor pypdf is available; run install.sh")
    r = PdfReader(a.pdf)
    lo = int(first) - 1 if first else 0
    hi = int(last or first) if first else len(r.pages)
    for i in range(lo, min(hi, len(r.pages))):
        sys.stdout.write(f"\n--- page {i + 1} ---\n" + (r.pages[i].extract_text() or ""))


if __name__ == "__main__":
    main()
