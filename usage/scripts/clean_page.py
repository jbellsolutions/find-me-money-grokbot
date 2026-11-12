#!/usr/bin/env python3
"""Print only the readable words of a web page (no menus, scripts, ads, code).

usage: clean_page.py <url-or-html-file> [--max-chars N]
Uses trafilatura when installed, else a stdlib fallback.
"""
import argparse
import html.parser
import pathlib
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; usage-saver/1.0)"
SKIP = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "button", "iframe"}


def fetch(src: str) -> str:
    if re.match(r"^https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    return pathlib.Path(src).read_text(errors="replace")


class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.depth += 1
        elif tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.out.append(data)


def fallback(html_text: str) -> str:
    p = _Text()
    p.feed(html_text)
    lines = [re.sub(r"\s+", " ", l).strip() for l in "".join(p.out).splitlines()]
    # keep lines that look like prose, drop short menu crumbs
    keep = [l for l in lines if len(l) > 40 or (l.endswith((".", "?", "!", ":")) and len(l) > 15)]
    return "\n".join(keep)


def clean(html_text: str) -> str:
    try:
        import trafilatura  # type: ignore

        out = trafilatura.extract(html_text, include_comments=False, include_tables=True)
        if out:
            return out
    except Exception:
        pass
    return fallback(html_text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--max-chars", type=int, default=8000)
    a = ap.parse_args()
    raw = fetch(a.src)
    text = clean(raw)
    if len(text) > a.max_chars:
        text = text[: a.max_chars] + f"\n[... cut at {a.max_chars} of {len(text)} chars]"
    sys.stdout.write(text + "\n")
    sys.stderr.write(f"clean_page: {len(raw)} chars in, {min(len(text), a.max_chars)} out\n")


if __name__ == "__main__":
    main()
