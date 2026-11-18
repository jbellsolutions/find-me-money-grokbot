#!/usr/bin/env python3
"""Dream 500: place a list by audience size, and show what a day can carry. Reads and writes files only; sends nothing.

    dream500.py check <settings.json>                         problems in a settings file, one per line; exit 0 if none
    dream500.py place <list.csv> --settings <s.json> --out <dir>
                                                              split the list into dream-500.csv, to-dream-100.csv,
                                                              to-partners.csv, needs-audience.csv, no-contact.csv
    dream500.py plan --settings <s.json> [--ready N] [--followups N]
                                                              the day's email number and which limit set it
    dream500.py selftest

Bands (PROCESS.md, step 2): audience >= dream_100_from goes to Dream 100; >= dream_500_from stays here; under it goes to
the wide partners tier. The audience column is read as given; a row with no readable number goes to needs-audience.csv.
"""
import csv, json, re, sys, tempfile
from pathlib import Path

REACH = ["email", "linkedin_url", "x_url", "instagram_url", "community_url"]
FILES = {"500": "dream-500.csv", "100": "to-dream-100.csv", "partners": "to-partners.csv",
         "needs": "needs-audience.csv", "nocontact": "no-contact.csv"}


def load(path):
    return json.loads(Path(path).read_text())


def check(s):
    out = []
    b = s.get("bands", {})
    hi, lo = b.get("dream_100_from"), b.get("dream_500_from")
    if not (isinstance(hi, int) and isinstance(lo, int) and 0 < lo < hi):
        out.append("bands: dream_500_from and dream_100_from must be whole numbers, the first smaller")
    n = s.get("first_batch", {}).get("approve_first")
    if not (isinstance(n, int) and n >= 1):
        out.append("first_batch.approve_first: at least 1 (the owner reads the first 5 or 10)")
    if s.get("state") not in ("off", "test", "on"):
        out.append("state: off, test or on")
    f = s.get("fill", {})
    for k in ("what_we_do", "episode_title", "episode_url", "signs_as", "unsubscribe_line"):
        if not str(f.get(k, "")).strip():
            out.append(f"fill.{k}: empty")
    e = s.get("email", {})
    if e.get("on"):
        if not (isinstance(e.get("emails_per_day_target"), int) and e["emails_per_day_target"] > 0):
            out.append("email.emails_per_day_target: a whole number above 0")
        if not 0 < float(e.get("share_of_capacity", 0)) <= 1:
            out.append("email.share_of_capacity: above 0, at most 1")
    blob = json.dumps(s)
    if re.search(r"(sk-|xox[bp]-|api[_-]?key\"\s*:\s*\"[^\"]+)", blob, re.I):
        out.append("something that looks like a key is in the file")
    return out


def number(v):
    """'250,000', '250k', '1.2M' -> int; anything else -> None."""
    t = str(v or "").strip().lower().replace(",", "").replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([km]?)", t)
    if not m:
        return None
    return int(float(m.group(1)) * {"": 1, "k": 1_000, "m": 1_000_000}[m.group(2)])


def key_of(row):
    e = (row.get("email") or "").strip().lower()
    if e:
        return "e:" + e
    for c in REACH[1:]:
        u = (row.get(c) or "").strip().lower().rstrip("/")
        if u:
            return "u:" + re.sub(r"^https?://(www\.)?", "", u)
    return ""


def place(rows, bands):
    hi, lo = bands["dream_100_from"], bands["dream_500_from"]
    best, order, out = {}, [], {k: [] for k in FILES}
    for r in rows:
        r = {k: (v or "").strip() for k, v in r.items() if k}
        if not r.get("first_name") and r.get("name"):
            r["first_name"] = r["name"].split()[0]
        k = key_of(r)
        if not k:
            out["nocontact"].append(r)
            continue
        n = number(r.get("audience"))
        r["_n"] = n
        if k not in best:
            order.append(k)
            best[k] = r
        elif (r["_n"] or -1) > (best[k]["_n"] or -1):
            best[k] = r
    for k in order:
        r = best[k]
        n = r.pop("_n")
        out["needs" if n is None else "100" if n >= hi else "500" if n >= lo else "partners"].append(r)
    return out


def write(out, cols, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for k, name in FILES.items():
        with open(folder / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(out[k])


def plan(s, ready=None, followups=0):
    e = s.get("email", {})
    limits = {"the target": e.get("emails_per_day_target", 0)}
    cap = int(e.get("inbox_count", 0) * e.get("per_inbox_per_day", 0) * float(e.get("share_of_capacity", 1)))
    limits["what the inboxes carry"] = cap
    if ready is not None:
        limits["rows ready plus follow-ups due"] = ready + followups
    why = min(limits, key=limits.get)
    return {"send_today": limits[why], "limited_by": why, "limits": limits}


def arg(a, name, default=None):
    return a[a.index(name) + 1] if name in a else default


def selftest():
    ok = []
    def t(name, cond):
        ok.append(cond)
        print(("ok   " if cond else "FAIL ") + name)
    here = Path(__file__).parent
    s = load(here / "dream500.example.json")
    probs = check(s)
    t("example settings: only the unfilled names are flagged", probs == [] or all(p.startswith("fill.") for p in probs))
    rows = [
        {"name": "Ada Big", "audience": "2.5M", "audience_source": "u", "email": "a@x.test"},
        {"name": "Bo Mid", "audience": "250,000", "audience_source": "u", "email": "b@x.test"},
        {"name": "Bo Mid", "audience": "400k", "audience_source": "u", "email": "B@x.test"},
        {"name": "Cy Edge", "audience": "100000", "audience_source": "u", "x_url": "https://x.com/cy/"},
        {"name": "Di Top", "audience": "1000000", "audience_source": "u", "x_url": "https://x.com/di"},
        {"name": "Ed Small", "audience": "99999", "audience_source": "u", "email": "e@x.test"},
        {"name": "Flo Unknown", "audience": "lots", "audience_source": "u", "email": "f@x.test"},
        {"name": "Hal Nowhere", "audience": "300000", "audience_source": "u"},
    ]
    o = place(rows, s["bands"])
    names = lambda k: [r["name"] for r in o[k]]
    t("1,000,000 and over goes to Dream 100", names("100") == ["Ada Big", "Di Top"])
    t("100,000 up to 999,999 stays, edge included", names("500") == ["Bo Mid", "Cy Edge"])
    t("a duplicate is kept once, with the larger audience", o["500"][0]["audience"] == "400k")
    t("under 100,000 goes to the partners tier", names("partners") == ["Ed Small"])
    t("no readable number is set aside", names("needs") == ["Flo Unknown"])
    t("no way to reach them is set aside", names("nocontact") == ["Hal Nowhere"])
    t("first name is filled from the name", o["500"][0]["first_name"] == "Bo")
    with tempfile.TemporaryDirectory() as d:
        write(o, ["name", "first_name", "audience", "audience_source"] + REACH, d)
        t("five files are written", sorted(p.name for p in Path(d).iterdir()) == sorted(FILES.values()))
    s2 = json.loads(json.dumps(s))
    s2["email"].update(inbox_count=20, per_inbox_per_day=30)
    p = plan(s2, ready=5000, followups=100)
    t("the inboxes limit the day when they carry less than the target",
      p["send_today"] == 600 and p["limited_by"] == "what the inboxes carry")
    s2["email"].update(inbox_count=50)
    t("the target limits the day when the inboxes carry more", plan(s2, ready=5000)["send_today"] == 1000)
    t("rows ready limit the day when the list is short", plan(s2, ready=40, followups=10)["send_today"] == 50)
    s3 = json.loads(json.dumps(s))
    s3["first_batch"]["approve_first"] = 0
    t("a first batch of zero is refused", any("approve_first" in x for x in check(s3)))
    s3["email"]["api_key"] = "abc123"
    t("a key-shaped value in the settings is refused", any("key" in x for x in check(s3)))
    print(f"\n{sum(ok)} of {len(ok)} passed")
    return 0 if all(ok) else 1


def main(a):
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    if a[0] == "selftest":
        return selftest()
    if a[0] == "check":
        probs = check(load(a[1]))
        print("\n".join(probs) if probs else "ok")
        return 1 if probs else 0
    if a[0] == "place":
        s = load(arg(a, "--settings"))
        with open(a[1], newline="", encoding="utf-8-sig") as f:
            rd = csv.DictReader(f)
            rows, cols = list(rd), [c for c in (rd.fieldnames or []) if c]
        if "first_name" not in cols:
            cols.insert(1, "first_name")
        o = place(rows, s["bands"])
        write(o, cols, arg(a, "--out", "."))
        for k, name in FILES.items():
            print(f"{len(o[k]):>6}  {name}")
        return 0
    if a[0] == "plan":
        r = arg(a, "--ready")
        print(json.dumps(plan(load(arg(a, "--settings")), int(r) if r else None, int(arg(a, "--followups", 0))), indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
