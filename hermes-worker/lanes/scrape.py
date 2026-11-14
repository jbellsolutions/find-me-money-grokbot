#!/usr/bin/env python3
"""Craigslist real-estate poster scraper: one JSONL row per post, from the public no-JavaScript search pages.

  scrape.py run --sites tampa,orlando --cats all          # list pages + the new posts' pages, rows -> data/posts.jsonl
  scrape.py run --all                                     # every US site in sites.json (416)
  scrape.py run --sites tampa --dry-run                   # list pages only, no post pages
  scrape.py report [--now ISO]                            # counts per site and category, from data/
  scrape.py reclassify                                    # re-apply the kind/signal/phone rules to saved text (no network)
  scrape.py google --max-credits 8                        # the fallback: Google site: searches via ScrapeCreators
  scrape.py selftest                                      # offline checks of the parsers and rules

How it reads (see README.md): https://www.craigslist.org/search/area/<site>?cat=<code> answers plain HTTP with a static
list (title, price, place, link; newest-updated first). A post's own page gives the numeric post id, posted/updated times
and body. Nothing here logs in, solves a captcha, rotates addresses or user agents, or contacts anyone. It runs one
request at a time with a fixed delay, and stops the whole run at the first sign of a block (403, 429, a captcha page, or
a list that was full last time and is empty now). Exit codes: 0 done, 2 bad arguments, 3 blocked, 4 stopped at the request cap
(so a truncated run never looks successful).

Stdlib plus httpx only. State lives in DATA_DIR (default ./data, override with CL_RE_DATA_DIR): state.sqlite (what was
seen, post text for re-classifying), posts.jsonl (the output, one row per post id), runs.jsonl (one summary per run).
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("CL_RE_DATA_DIR") or HERE / "data")
BASE = "https://www.craigslist.org"
UA = "PinnacleFundingResearch/1.0"  # fixed and honest; never rotated
STOP_AFTER_OLD = 3  # consecutive posts (new to us or already seen) older than the window that end a list

# ----------------------------------------------------------------------------------------------------------- categories
# code -> (Craigslist query string, label as Craigslist shows it, what the poster is, absent any other evidence)
CATEGORIES = {
    "rea-owner": ("cat=rea&purveyor=owner", "real estate for sale - by owner", "owner_seller"),
    "rea-broker": ("cat=rea&purveyor=dealer", "real estate for sale - by broker", "broker"),
    "rew": ("cat=rew", "wanted: real estate", "other"),
    "rts": ("cat=rts", "services: real estate", "other"),
    "off": ("cat=off", "office & commercial", "other"),
    "hsw": ("cat=hsw", "housing wanted", "other"),
    # Find Me Money GrokBot business lane (added 2026-11-12). The live radar-cl service keeps the real-estate set;
    # the bot reads only these, so the two never read the same lists. Check each with --dry-run before a full run.
    "bfs": ("cat=bfs", "business for sale", "other"),
    "fns": ("cat=fns", "services: financial", "other"),
    "sks": ("cat=sks", "services: skilled trade", "other"),
}
BIZ_CATS = ("bfs", "fns", "sks")  # --cats biz
DEFAULT_CATS = ("rea-owner", "rea-broker", "rew", "rts")  # off and hsw are measured but left out of the daily run (README)

# ----------------------------------------------------------------------------------------------------------- the rules
# Signals: a name for each phrase family. A post's text is its title plus body, lower-cased, curly quotes straightened.
# words allowed between "we buy" and "houses" ("we buy any distressed houses"), so "we buy and sell homes" does not match
_MOD = r"(?:(?:your|any|all|ugly|distressed|rental|investment|residential|vacant|inherited|fixer[- ]uppers?|single[- ]family|probate|foreclosed|older|damaged|run[- ]down)\s+){0,3}"
SIGNALS: list[tuple[str, str]] = [
    ("cash buyers", r"\bcash[- ]buyers?\b"),
    ("cash only", r"\bcash[- ]only\b|\bcash deals? only\b|\ball[- ]cash\b"),
    ("cash offer", r"\bcash offers?\b|\bpay(?:ing)? cash\b|\bfor cash\b|\bcash for (?:your |any )?(?:house|home|property|land)\b"),
    ("we buy houses", r"\b(?:we|i)(?:'ll| will)?[- ](?:buy|purchase)s?\s+" + _MOD + r"(?:houses?|homes?|properties|property|land|lots?|condos?|apartments?|mobile homes?|real estate)\b"
                      r"|\b(?:we|i)(?:'re| are| am)? (?:now |currently |actively )?buying\s+" + _MOD + r"(?:houses|homes|properties|real estate|land)\b"
                      r"|\b(?:we|i)(?:'d| would)? (?:want|wish|love|like|plan)s? to buy (?:your|ur) \w+|\binterested in buying (?:your|ur) \w+"),
    ("sell fast", r"\bsell (?:your |my )?(?:house|home|property)(?: \w+)?\s*(?:fast|quick(?:ly)?|now|as[- ]is)\b"),
    ("quick close", r"\bclose in \d+ days\b|\bquick clos(?:e|ing)\b|\bfast clos(?:e|ing)\b"),
    ("as-is", r"\bas[- ]is\b|\bany condition\b"),
    ("ARV", r"\barv\b|\bafter[- ]repair(?:ed)? value\b"),
    ("assignment", r"\bassignment\b|\bassignable\b|\bassign(?:ing)? (?:the |this |my |our )?(?:contract|purchase|agreement)\b"),
    ("wholesale", r"\bwholesal(?:e|er|ers|ing)\b"),
    ("double close", r"\bdouble[- ]clos(?:e|ing)\b"),
    ("equitable interest", r"\bequitable interest\b"),
    ("buyers list", r"\bbuyer'?s'? list\b|\bbuyers? network\b"),
    ("off market", r"\boff[- ]?market\b|\bpocket listing\b|\bnot on (?:the )?mls\b"),
    ("under contract", r"\bunder contract\b|\bunder purchase agreement\b"),
    ("investor special", r"\binvestor(?:'?s)? (?:special|opportunity|deal|property|pricing)\b|\b(?:great|perfect|ideal|ready) (?:for|to) (?:an? )?investors?\b|\binvestors? (?:only|welcome|wanted|needed|alert)\b|\bfor investors?\b"),
    ("investor", r"\binvestors?\b|\binvestment (?:property|opportunity|deal|home)\b"),
    ("flip", r"\bflip(?:per|pers|ping|s)?\b|\bfix(?:[- ]and[- ]|[- ]n[- ]|[- ]&[- ])flip\b"),
    ("fixer", r"\bfixer[- ]?upper\b|\bhandy ?man(?:'?s)? special\b|\bneeds? (?:tlc|work|repairs?|rehab)\b|\brehab\b|\bdistressed\b|\bgutted\b"),
    ("hard money", r"\bhard[- ]money\b"),
    ("private money", r"\bprivate[- ]money\b|\bprivate lenders?\b"),
    ("bridge loan", r"\bbridge (?:loans?|financing|lenders?)\b"),
    ("DSCR", r"\bdscr\b"),
    ("proof of funds", r"\bproof of funds\b|\bpof\b|\btransactional fund(?:ing|s)\b"),
    ("EMD", r"\bemd\b|\bearnest money\b"),
    ("seller financing", r"\b(?:seller|owner)[- ]financ(?:e|ing|ed)\b|\bowner will carry\b|\bowc\b|\bland contract\b|\bcontract for deed\b"),
    ("creative finance", r"\bsubject[- ]to (?:the )?(?:existing|current)\b|\bsub2\b|\bsubto\b|\blease[- ]option\b|\brent[- ]to[- ]own\b|\bwraparound\b"),
    ("motivated seller", r"\bmotivated seller\b|\bmust sell\b|\bpre-?foreclosure\b|\bforeclosure\b|\bprobate\b|\bestate sale\b|\bdivorce\b|\btax deed\b"),
    ("multifamily", r"\bmulti[- ]?family\b|\bduplex\b|\btriplex\b|\bfourplex\b|\bquadplex\b|\b\d{1,3}[- ]units?\b|\bapartment (?:building|complex)\b"),
    ("rental income", r"\bturn[- ]?key\b|\bportfolio\b|\bcap rate\b|\bnoi\b|\bcash[- ]?flow\b|\brent roll\b|\b1031\b|\bsection 8\b"),
    ("land", r"\bvacant (?:land|lot)\b|\bacreage\b|\bbuildable lots?\b|\bdevelopment (?:site|land|opportunity)\b|\bentitled\b"),
    ("new construction", r"\bnew construction\b|\bspec homes?\b|\bbuilder\b"),
    ("wants to buy", r"\b(?:looking|wanted|want|need|seeking|searching)\b.{0,40}\b(?:to buy|buy|purchase)\b|\bwanted:"),
    ("agent", r"\brealtors?\b|\bbroker(?:age)?\b|\blicen[sc]ed (?:real estate|realtor|agent|broker)\b|\bmls\b|\blisting agent\b|\bre/?max\b|\bkeller williams\b|\bcoldwell banker\b|\bcentury ?21\b|\bexp realty\b|\bsotheby|\bsold by\b|\blisted by\b|\bcourtesy of\b"),
]
_LENDER = [r"\bhome loans?\b", r"\bmortgage", r"\bpre-?approv", r"\bnmls\b", r"\bloan officers?\b", r"\brefinanc", r"\bheloc\b",
           r"\bfha\b", r"\bva loans?\b", r"\bdown payment assistance\b", r"\bcredit score", r"\btold ['\"]?no\b", r"\bwe (?:offer|provide|lend|fund|finance)\b.{0,30}\b(?:loans?|funding|financing)\b",
           r"\b(?:loans?|funding|financing) (?:available|offered)\b"]
STRONG_WHOLESALE = {"assignment", "wholesale", "double close", "equitable interest", "buyers list"}
WEAK_WHOLESALE = {"off market", "under contract", "investor special", "ARV", "cash only", "cash buyers"}
BUYER_SIGNS = {"we buy houses", "sell fast"}
_COMPILED = [(name, re.compile(rx, re.I)) for name, rx in SIGNALS]
_LENDER_RE = [re.compile(rx, re.I) for rx in _LENDER]


def norm_text(s: str) -> str:
    return (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').lower()


def find_signals(title: str, body: str) -> list[str]:
    text = norm_text(f"{title}\n{body}")
    found = [name for name, rx in _COMPILED if rx.search(text)]
    head = norm_text(title)
    lender_hits = sum(1 for rx in _LENDER_RE if rx.search(text))
    if lender_hits >= 2 or any(rx.search(head) for rx in _LENDER_RE):
        found.append("lender ad")
    return found


def decide_kind(category: str, signals: list[str]) -> str:
    """owner_seller | wholesaler | investor_buyer | broker | other. First rule that fires wins."""
    s = set(signals)
    if s & STRONG_WHOLESALE:
        return "wholesaler"
    if "lender ad" in s and not (s & BUYER_SIGNS):
        return "other"  # a lender advertising (a competitor or partner), not a borrower
    if s & BUYER_SIGNS:
        return "investor_buyer"
    if category == "rew" and (s & {"cash buyers", "cash offer", "hard money", "private money", "proof of funds"}):  # "wants to buy" alone is an ordinary buyer
        return "investor_buyer"
    if len(s & WEAK_WHOLESALE) >= 2 and "agent" not in s:
        return "wholesaler"
    if "agent" in s or category == "rea-broker":
        return "broker"
    if category == "rea-owner":
        return "owner_seller"
    return CATEGORIES[category][2]


# phone: only what the post body (or title) prints. Ten digits with no separator count only after a phone word.
PHONE_RE = re.compile(r"(?<![\w$.,])(?:\+?1[\s.\-]?)?(?:\((?P<a1>[2-9]\d{2})\)|(?P<a2>[2-9]\d{2}))[\s.\-]*(?P<x>[2-9]\d{2})[\s.\-]*(?P<n>\d{4})(?!\d)")
PHONE_CTX = re.compile(r"(?:call|text|phone|cell|tel|contact|reach|mobile|office|whatsapp|dial|ph)\W{0,12}$", re.I)
PHONE_BAD_CTX = re.compile(r"(?:mls|id|parcel|folio|apn|listing|ref|reference|lot|permit|license|lic)\W{0,6}#?\W{0,3}$", re.I)


def find_phone(text: str) -> str | None:
    for m in PHONE_RE.finditer(text or ""):
        raw = m.group(0)
        before = text[max(0, m.start() - 30):m.start()]
        bare = re.fullmatch(r"\+?\d{10,11}", raw) is not None  # digits only, no separators
        if PHONE_BAD_CTX.search(before):
            continue
        if bare and not PHONE_CTX.search(before):
            continue
        return f"{m.group('a1') or m.group('a2')}-{m.group('x')}-{m.group('n')}"
    return None


# ----------------------------------------------------------------------------------------------------------- parsing
_LIST_ITEM = re.compile(r'<li class="cl-static-search-result" title="(?P<title>.*?)">\s*<a href="(?P<url>[^"]+)">(?P<inner>.*?)</li>', re.S)
_PRICE = re.compile(r'<div class="price">\s*(.*?)\s*</div>', re.S)
_LOC = re.compile(r'<div class="location">\s*(.*?)\s*</div>', re.S)


def token_of(url: str) -> str:
    """The stable end of a post link: .../view/d/<slug>/<token>  or  .../<cat>/d/<slug>/<number>.html"""
    return re.sub(r"\.html$", "", url.split("?")[0].rstrip("/").rsplit("/", 1)[-1])


def parse_price(s: str | None) -> int | None:
    m = re.search(r"\$\s*([\d,]+)", s or "")
    return int(m.group(1).replace(",", "")) if m and m.group(1).replace(",", "") else None


def parse_list(page: str) -> list[dict]:
    out = []
    for m in _LIST_ITEM.finditer(page):
        inner = m.group("inner")
        price, loc = _PRICE.search(inner), _LOC.search(inner)
        out.append({"token": token_of(m.group("url")), "url": htmllib.unescape(m.group("url")),
                    "title": htmllib.unescape(m.group("title")).strip(),
                    "price": parse_price(price.group(1) if price else None),
                    "city": htmllib.unescape(re.sub(r"\s+", " ", loc.group(1))).strip() if loc else None})
    return out


_VOID = {"br", "img", "input", "hr", "meta", "link", "wbr", "source"}


class _Body(HTMLParser):
    """Text of <section id=postingbody>, minus the print-only QR-code block."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.sections = 0
        self.skip = 0
        self.done = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.done:
            return
        if self.sections == 0:
            if tag == "section" and a.get("id") == "postingbody":
                self.sections = 1
            return
        if tag == "section":
            self.sections += 1
        if self.skip:
            if tag not in _VOID:
                self.skip += 1
            return
        if "print-information" in (a.get("class") or ""):
            self.skip = 1
            return
        if tag == "br":
            self.parts.append("\n")
        elif tag in ("p", "div", "li", "ul", "ol", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.done or self.sections == 0:
            return
        if self.skip:
            if tag not in _VOID:
                self.skip -= 1
            return
        if tag == "section":
            self.sections -= 1
            if self.sections == 0:
                self.done = True
        elif tag in ("p", "div", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.sections and not self.skip and not self.done:
            self.parts.append(data)


def body_text(page: str) -> str:
    p = _Body()
    p.feed(page)
    txt = "".join(p.parts)
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t\r\f\v]+", " ", txt)).strip()


def parse_when(s: str | None) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z") if s else None
    except ValueError:
        return None


def parse_post(page: str) -> dict | None:
    """None when the page isn't a live post (deleted, flagged, or not a post at all)."""
    pid = re.search(r"post id:\s*(\d+)", page)
    if not pid or 'id="postingbody"' not in page:
        return None
    posted = re.search(r'posted:\s*<time[^>]*datetime="([^"]+)"', page) or re.search(r'id="display-date"[^>]*>\s*Posted\s*<time[^>]*datetime="([^"]+)"', page)
    upd = re.search(r'updated:\s*<time[^>]*datetime="([^"]+)"', page)
    title = re.search(r'<span id="titletextonly">(.*?)</span>', page, re.S)
    city = re.search(r'<span id="titletextonly">.*?</span>\s*<span>\s*\((.*?)\)\s*</span>', page, re.S)
    price = re.search(r'<span class="postingtitletext">\s*<span class="price">(.*?)</span>', page, re.S)
    area = re.search(r'"item":"https://www\.craigslist\.org/area/([a-z0-9-]+)"', page)
    return {"id": int(pid.group(1)), "posted": parse_when(posted.group(1) if posted else None),
            "updated": parse_when(upd.group(1) if upd else None),
            "title": htmllib.unescape(title.group(1)).strip() if title else None,
            "city": htmllib.unescape(city.group(1)).strip() if city else None,
            "price": parse_price(price.group(1) if price else None),
            "site": area.group(1) if area else None, "body": body_text(page)}


# ----------------------------------------------------------------------------------------------------------- fetching
class Blocked(RuntimeError):
    """Craigslist is refusing us. The run stops; nothing tries to get around it."""


class CapReached(RuntimeError):
    pass


class Fetcher:
    def __init__(self, delay: float, max_requests: int):
        import httpx
        self.httpx = httpx
        self.client = httpx.Client(headers={"User-Agent": UA, "Accept": "text/html"}, timeout=30, follow_redirects=True)
        self.delay, self.max = delay, max_requests
        self.n, self.bytes, self.last = 0, 0, 0.0
        self.status: Counter = Counter()

    def get(self, url: str) -> str | None:
        """The page text; None for a 404. Raises Blocked on 403/429 or a captcha page, CapReached at the request cap."""
        for attempt in (1, 2):
            if self.n >= self.max:
                raise CapReached(f"request cap {self.max}")
            wait = self.delay - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.n += 1
            try:
                r = self.client.get(url)
            except self.httpx.HTTPError as exc:
                self.last = time.monotonic()
                self.status[type(exc).__name__] += 1
                if attempt == 2:
                    raise Blocked(f"transport error twice: {type(exc).__name__}")
                time.sleep(10)
                continue
            self.last = time.monotonic()
            self.status[r.status_code] += 1
            self.bytes += len(r.content)
            if r.status_code in (403, 429):
                raise Blocked(f"HTTP {r.status_code} on {url}")
            if r.status_code == 404:
                return None
            if r.status_code >= 500:
                if attempt == 2:
                    raise Blocked(f"HTTP {r.status_code} twice on {url}")
                time.sleep(10)
                continue
            text = r.text
            if re.search(r"h-?captcha|g-recaptcha|cf-challenge|are you a (?:human|robot)", text[:20000], re.I) and "cl-static-search-results" not in text and 'id="postingbody"' not in text:
                raise Blocked(f"captcha or challenge page on {url}")
            return text
        return None


# ----------------------------------------------------------------------------------------------------------- state
def open_db() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATA / "state.sqlite")
    db.executescript("""
        create table if not exists seen (token text primary key, post_id integer, site text, category text, posted_at text,
            updated_at text, emitted integer not null default 0, first_seen text not null);
        create unique index if not exists seen_post_id on seen(post_id) where post_id is not null;
        create table if not exists posts (post_id integer primary key, row_json text not null, body text not null default '');
        create table if not exists lists (site text, category text, last_count integer, last_run text, primary key (site, category));
    """)
    return db


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def make_row(site: str, category: str, listing: dict, post: dict) -> tuple[dict, str]:
    title = post["title"] or listing["title"]
    signals = find_signals(title, post["body"])
    row = {"id": post["id"], "site": post["site"] or site, "city": listing.get("city") or post["city"], "category": category,
           "title": title, "price": listing["price"] if listing["price"] is not None else post["price"],
           "posted_at": iso(post["posted"]), "url": listing["url"], "kind": decide_kind(category, signals),
           "signals": signals, "phone": find_phone(f"{title}\n{post['body']}")}
    return row, post["body"]


# ----------------------------------------------------------------------------------------------------------- run
def load_sites() -> list[dict]:
    return json.loads((HERE / "sites.json").read_text())["sites"]


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def run(args) -> int:
    sites = load_sites()
    known = {s["site"] for s in sites}
    if args.all:
        chosen = [s["site"] for s in sites]
    else:
        chosen = [x.strip() for x in (args.sites or "").split(",") if x.strip()]
        bad = [x for x in chosen if x not in known]
        if bad:
            log(f"unknown site(s) {bad}; see sites.json")
            return 2
    cats = list(DEFAULT_CATS) if args.cats in ("", "default") else list(BIZ_CATS) if args.cats == "biz" else list(CATEGORIES) if args.cats == "all" else [c.strip() for c in args.cats.split(",") if c.strip()]
    if any(c not in CATEGORIES for c in cats):
        log(f"unknown category in {cats}; choose from {list(CATEGORIES)}")
        return 2
    if args.max_requests is None:
        args.max_requests = 12000 if args.all else 1500
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=args.max_age_hours)
    db = open_db()
    out_path = Path(args.out) if args.out else DATA / "posts.jsonl"
    out = open(out_path, "a", encoding="utf-8")
    f = Fetcher(args.delay, args.max_requests)
    t0 = time.monotonic()
    per: dict[str, dict[str, dict]] = defaultdict(dict)
    stop_reason = None
    emitted = 0
    try:
        for site in chosen:
            for cat in cats:
                st = per[site][cat] = {"listed": 0, "seen_skipped": 0, "fetched": 0, "emitted": 0, "old": 0, "deleted": 0, "dup_id": 0}
                page = f.get(f"{BASE}/search/area/{site}?{CATEGORIES[cat][0]}")
                if page is None:
                    st["error"] = "404"
                    continue
                items = parse_list(page)
                st["listed"] = len(items)
                prev = db.execute("select last_count from lists where site=? and category=?", (site, cat)).fetchone()
                if not items and prev and prev[0] >= 10 and "cl-static-search-results" in page:
                    raise Blocked(f"{site}/{cat}: list empty now, had {prev[0]} last run")
                if not items and "cl-static-search-results" not in page:
                    raise Blocked(f"{site}/{cat}: no result list in the page (layout changed or a block page)")
                db.execute("insert or replace into lists values (?,?,?,?)", (site, cat, len(items), now.isoformat()))
                db.commit()
                if args.dry_run:
                    continue
                old_streak = 0
                for it in items:
                    hit = db.execute("select emitted, post_id from seen where token=?", (it["token"],)).fetchone()
                    if hit:  # seen before: no request. A run of seen-and-old posts means the rest of the list is old too.
                        st["seen_skipped"] += 1
                        if hit[1] is not None:
                            old_streak = old_streak + 1 if hit[0] == 0 else 0
                            if old_streak >= STOP_AFTER_OLD:
                                break
                        continue
                    if st["fetched"] >= args.max_posts_per_list:
                        st["capped"] = True
                        break
                    ppage = f.get(it["url"])
                    st["fetched"] += 1
                    post = parse_post(ppage) if ppage else None
                    stamp = datetime.now(timezone.utc).isoformat()
                    if not post:
                        db.execute("insert into seen (token, site, category, emitted, first_seen) values (?,?,?,0,?)", (it["token"], site, cat, stamp))
                        db.commit()
                        st["deleted"] += 1
                        continue
                    newest = post["updated"] or post["posted"]
                    if db.execute("select 1 from seen where post_id=?", (post["id"],)).fetchone():
                        db.execute("insert into seen (token, site, category, emitted, first_seen) values (?,?,?,0,?)", (it["token"], site, cat, stamp))
                        db.commit()
                        st["dup_id"] += 1
                        continue
                    is_old = bool(newest and newest < cutoff)
                    db.execute("insert into seen (token, post_id, site, category, posted_at, updated_at, emitted, first_seen) values (?,?,?,?,?,?,?,?)",
                               (it["token"], post["id"], post["site"] or site, cat, iso(post["posted"]), iso(post["updated"]), 0 if is_old else 1, stamp))
                    if is_old:
                        db.commit()
                        st["old"] += 1
                        old_streak += 1
                        if old_streak >= STOP_AFTER_OLD:  # the list is newest-updated first: the rest is older still
                            break
                        continue
                    old_streak = 0
                    row, body = make_row(site, cat, it, post)
                    db.execute("insert into posts values (?,?,?)", (row["id"], json.dumps(row, ensure_ascii=False), body))
                    db.commit()
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    out.flush()
                    st["emitted"] += 1
                    emitted += 1
                log(f"{site:14s} {cat:10s} listed {st['listed']:3d}  skipped {st['seen_skipped']:3d}  fetched {st['fetched']:3d}  "
                    f"new {st['emitted']:3d}  old {st['old']}  [{f.n} req, {time.monotonic() - t0:.0f}s]")
    except Blocked as exc:
        stop_reason = f"BLOCKED: {exc}"
    except CapReached as exc:
        stop_reason = f"CAP: {exc}"
    except KeyboardInterrupt:
        stop_reason = "interrupted"
    finally:
        out.close()
    summary = {"started": now.isoformat(), "seconds": round(time.monotonic() - t0, 1), "requests": f.n, "bytes": f.bytes,
               "statuses": dict(f.status), "delay": args.delay, "max_age_hours": args.max_age_hours, "sites": len(chosen),
               "categories": cats, "rows_written": emitted, "stopped": stop_reason, "dry_run": args.dry_run,
               "per_site": {s: c for s, c in per.items()}, "out": str(out_path)}
    with open(DATA / "runs.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(summary) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_site"}, indent=1))
    if stop_reason and stop_reason.startswith("BLOCKED"):
        return 3
    return 4 if stop_reason and stop_reason.startswith("CAP") else 0


# ----------------------------------------------------------------------------------------------------------- report
def report(args) -> int:
    path = Path(args.posts) if args.posts else DATA / "posts.jsonl"
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    d24 = now - timedelta(hours=24)
    tab: dict = defaultdict(lambda: {"rows": 0, "posted_24h": 0, "inv": 0, "phone": 0})
    kinds: Counter = Counter()
    for r in rows:
        t = datetime.fromisoformat(r["posted_at"]) if r.get("posted_at") else None
        for key in ((r["site"], r["category"]), (r["site"], "ALL"), ("ALL", r["category"]), ("ALL", "ALL")):
            c = tab[key]
            c["rows"] += 1
            c["posted_24h"] += 1 if t and t >= d24 else 0
            c["inv"] += 1 if r["kind"] in ("wholesaler", "investor_buyer") else 0
            c["phone"] += 1 if r.get("phone") else 0
        kinds[r["kind"]] += 1
    print(f"{'site':14s} {'category':10s} {'rows':>5s} {'posted<=24h':>11s} {'investor/wholesaler':>20s} {'phone':>6s}")
    for (site, cat), c in sorted(tab.items(), key=lambda kv: (kv[0][0] == "ALL", kv[0])):
        share = f"{c['inv']} ({100 * c['inv'] / c['rows']:.0f}%)" if c["rows"] else "-"
        print(f"{site:14s} {cat:10s} {c['rows']:5d} {c['posted_24h']:11d} {share:>20s} {c['phone']:6d}")
    print("kinds:", dict(kinds))
    return 0


def reclassify(args) -> int:
    db = open_db()
    rows = db.execute("select post_id, row_json, body from posts order by post_id").fetchall()
    path = Path(args.posts) if args.posts else DATA / "posts.jsonl"
    changed = 0
    with open(path, "w", encoding="utf-8") as fh:
        for pid, rj, body in rows:
            r = json.loads(rj)
            sig = find_signals(r["title"], body)
            kind, phone = decide_kind(r["category"], sig), find_phone(f"{r['title']}\n{body}")
            changed += (kind, sig, phone) != (r["kind"], r["signals"], r["phone"])
            r.update(kind=kind, signals=sig, phone=phone)
            db.execute("update posts set row_json=? where post_id=?", (json.dumps(r, ensure_ascii=False), pid))
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    db.commit()
    print(f"rewrote {len(rows)} rows to {path}; {changed} changed")
    return 0


# ----------------------------------------------------------------------------------------------------------- fallback: Google
GOOGLE_TERMS = [
    'site:craigslist.org "we buy houses" cash',
    'site:craigslist.org "cash buyers" ARV',
    'site:craigslist.org assignment wholesale "real estate"',
    'site:craigslist.org "hard money" OR "private money" investor',
    'site:craigslist.org "fix and flip" investor',
]


def google(args) -> int:
    """The fallback when direct reads are blocked: ScrapeCreators /v1/google/search, 1 credit per page of 10. Google can
    only sample: results are keyword matches, and a /view/d/ link names no city or category. Hard credit cap."""
    import httpx
    key = os.environ.get("SCRAPECREATORS_API_KEY", "")
    if not key:
        log("SCRAPECREATORS_API_KEY is not set (the key is never printed or stored by this script)")
        return 2
    c = httpx.Client(base_url="https://api.scrapecreators.com", headers={"x-api-key": key, "accept": "application/json"}, timeout=60)

    def get(path, params=None):
        r = c.get(path, params=params)
        if r.status_code == 402:
            raise SystemExit("out of ScrapeCreators credits")
        r.raise_for_status()
        return r.json()
    start = int(get("/v1/account/credit-balance").get("creditCount", 0))
    log(f"balance before: {start}")
    spent, seen_tokens, rows = 0, set(), []
    db = open_db()
    known = {t for (t,) in db.execute("select token from seen")}
    terms = args.term or GOOGLE_TERMS
    for term in terms:
        for page in range(1, args.pages + 1):
            if spent >= args.max_credits:
                log("credit cap reached")
                break
            data = get("/v1/google/search", {"query": term, "date_posted": args.date_posted, "page": page})
            spent += int(data.get("credits_charged") or 1)
            res = data.get("results") or []
            cl = [x for x in res if "craigslist.org" in (x.get("url") or "")]
            for x in cl:
                tok = token_of(x["url"])
                title, desc = x.get("title") or "", x.get("description") or ""
                sig = find_signals(title, desc)
                rows.append({"term": term, "url": x["url"], "token": tok, "title": title, "kind": decide_kind("rts", sig), "signals": sig,
                             "in_direct_state": tok in known, "view_link": "/view/" in x["url"]})
                seen_tokens.add(tok)
            log(f"{term[:60]:60s} page {page}: {len(res)} results, {len(cl)} craigslist")
            if not data.get("next_page"):
                break
    end = int(get("/v1/account/credit-balance").get("creditCount", 0))
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / "google-probe.jsonl", "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(json.dumps({"searches_credits": spent, "balance_before": start, "balance_after": end, "craigslist_results": len(rows),
                      "unique_posts": len(seen_tokens), "already_in_direct_state": sum(1 for r in rows if r["in_direct_state"]),
                      "view_links": sum(1 for r in rows if r["view_link"])}, indent=1))
    return 0


# ----------------------------------------------------------------------------------------------------------- selftest
def selftest(_args) -> int:
    ok = True

    def check(name, got, want):
        nonlocal ok
        if got != want:
            ok = False
            print(f"FAIL {name}: got {got!r}, want {want!r}")
    check("phone dashed", find_phone("call 813-555-0142 today"), "813-555-0142")
    check("phone parens", find_phone("Text (727) 555-0199 anytime"), "727-555-0199")
    check("phone bare after word", find_phone("cell 8135550142"), "813-555-0142")
    check("phone bare no context", find_phone("MLS# 2025412345 priced at $225,000"), None)
    check("phone price", find_phone("asking $1,200,000 or 3 bed 2 bath 1568 sqft"), None)
    check("phone none", find_phone("reply through craigslist"), None)
    s = find_signals("We buy houses cash any condition", "Close in 7 days. No fees. Investor here.")
    check("signals buy", {"we buy houses", "cash offer", "as-is", "investor"} <= set(s) or {"we buy houses", "as-is", "investor"} <= set(s), True)
    check("kind buyer", decide_kind("rts", s), "investor_buyer")
    s = find_signals("Wholesale deal Tampa ARV 250k", "Assignment fee 10k. Cash buyers only. Under contract.")
    check("kind wholesaler", decide_kind("rea-owner", s), "wholesaler")
    s = find_signals("3/2 Home for sale", "Listed by Jane Doe, REALTOR, Acme Realty. MLS 123. Investor special.")
    check("kind broker", decide_kind("rea-broker", s), "broker")
    s = find_signals("WERE YOU TOLD NO FOR A HOME LOAN?", "Pre-approved mortgage and FHA help. NMLS 12345")
    check("kind lender", decide_kind("rea-broker", s), "other")
    check("we buy and sell is not a buyer", "we buy houses" in find_signals("Realtor", "We buy and sell homes in Dallas"), False)
    check("home buyers is not a buyer", "we buy houses" in find_signals("Nice 3/2", "Great for first-time home buyers"), False)
    check("we buy any distressed houses", "we buy houses" in find_signals("x", "We buy any distressed houses fast"), True)
    check("i buy houses", "we buy houses" in find_signals("I Buy Houses 361.208.iBuy", ""), True)
    check("we want to buy your property", "we buy houses" in find_signals("We want to buy your property!", ""), True)
    check("rew: plain buyer is other", decide_kind("rew", find_signals("Looking to buy or build from Smyrna to Dunwoody", "wanted: 3 bed home")), "other")
    check("rew: cash buyer is investor", decide_kind("rew", find_signals("Cash Buyer", "")), "investor_buyer")
    check("assigned parking is not assignment", "assignment" in find_signals("Condo", "2 assigned parking spaces"), False)
    s = find_signals("Nice home", "Owner selling, great yard")
    check("kind owner", decide_kind("rea-owner", s), "owner_seller")
    page = ('<section id="postingbody"><div class="print-information print-qrcode-container"><p>QR Code Link</p>'
            '<div class="print-qrcode" data-location="x"></div></div>Hello<br>call 813-555-0142<br></section>')
    check("body strips qr", body_text(page), "Hello\ncall 813-555-0142")
    li = ('<ol class="cl-static-search-results"><li class="cl-static-search-result" title="A &amp; B"><a href="https://www.craigslist.org/view/d/a-b/XyZ123">'
          '<div class="title">A &amp; B</div><div class="details"><div class="price">$1,450</div><div class="location">\n Tampa\n </div></div></a></li></ol>')
    items = parse_list(li)
    check("list parse", [(i["token"], i["title"], i["price"], i["city"]) for i in items], [("XyZ123", "A & B", 1450, "Tampa")])
    check("token old style", token_of("https://tampa.craigslist.org/reb/d/some-slug/7712345678.html"), "7712345678")
    print("selftest", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="scrape")
    r.add_argument("--sites", help="comma-separated site names from sites.json (tampa,orlando,...)")
    r.add_argument("--all", action="store_true", help="every site in sites.json")
    r.add_argument("--cats", default="default", help=f"default, all, or a comma list of {list(CATEGORIES)}")
    r.add_argument("--max-age-hours", type=float, default=36, help="skip posts last updated longer ago than this (default 36)")
    r.add_argument("--delay", type=float, default=2.5, help="seconds between requests (default 2.5)")
    r.add_argument("--max-requests", type=int, default=None, help="hard cap on requests in one run (default 1500, or 12000 with --all); hitting it exits 4")
    r.add_argument("--max-posts-per-list", type=int, default=250)
    r.add_argument("--dry-run", action="store_true", help="read the list pages only")
    r.add_argument("--out", help="rows file (default DATA_DIR/posts.jsonl)")
    r.set_defaults(fn=run)
    p = sub.add_parser("report")
    p.add_argument("--posts")
    p.add_argument("--now")
    p.set_defaults(fn=report)
    p = sub.add_parser("reclassify")
    p.add_argument("--posts")
    p.set_defaults(fn=reclassify)
    p = sub.add_parser("google", help="fallback: Google site: searches via ScrapeCreators (key from env, capped)")
    p.add_argument("--term", action="append", help="a query (repeatable); default: five real-estate terms")
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--max-credits", type=int, default=8)
    p.add_argument("--date-posted", default="last-week", choices=["last-day", "last-week", "last-month"])
    p.set_defaults(fn=google)
    p = sub.add_parser("selftest")
    p.set_defaults(fn=selftest)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
