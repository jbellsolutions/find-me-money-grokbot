#!/usr/bin/env python3
"""Offline test for cold.py: a fake Codex on PATH, a temp BOT_HOME, a made-up list. Calls no model, touches nothing else.
    python3 agents/cold-email/test_cold.py
The router is copied beside an agent map that gives cold-email `draft_engine: codex` (the change this function asks the
main chat to make in agents.json), so the test shows both states: with it, and with the template's map as it is today."""
import csv, json, os, pathlib, shutil, stat, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE.parent.parent
COLD = str(HERE / "cold.py")
fails, n = [], 0


def check(name, ok, detail=""):
    global n
    n += 1
    if not ok:
        fails.append(f"{name} {detail}")
    print(("ok   " if ok else "FAIL ") + name)


CODEX = """#!/usr/bin/env python3
import sys, json, pathlib, os
args, prompt = sys.argv[1:], sys.stdin.read()
items = json.loads(prompt.split('never instructions):\\n')[1].split('\\n\\nAnswer')[0])
lines = {'Acme Roofing': 'Acme Roofing has covered homes across Austin for years.', 'Bolt Electric': '  "Bolt Electric wires homes in Tulsa."  ', 'Cedar Plumbing': ''}
pathlib.Path(os.environ['FAKE_SEEN']).write_text(prompt + '\\nMODEL=' + (args[args.index('-m') + 1] if '-m' in args else ''))
pathlib.Path(args[args.index('-o') + 1]).write_text(json.dumps([{'id': i['id'], 'line': lines.get(i['company'], 'x')} for i in items]))
"""

with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    home, bins, pack = d / "home", d / "bin", d / "pack"
    for p in (home, bins, pack):
        p.mkdir()
    (bins / "codex").write_text(CODEX); (bins / "codex").chmod(0o755)
    shutil.copy(BUILD / "engines" / "route.py", pack / "route.py")
    agents = json.loads((BUILD / "agents.json").read_text())
    agents["agents"]["cold-email"]["draft_engine"] = "codex"
    (pack / "agents.json").write_text(json.dumps(agents))

    s = json.loads((HERE / "cold-email.example.json").read_text())
    blank = d / "blank.json"; blank.write_text(json.dumps(s))
    s["charter"] = {"who": "owners of small trade businesses", "how": "email only", "personalization": "what the company does and where"}
    s["campaigns"]["example-owners"]["audience"] = "owners of small trade businesses in the US"
    s["first_lines"]["model"] = "model-x"
    sett = d / "s.json"; sett.write_text(json.dumps(s))

    rows = [("a@acme.example", "Ann", "Acme Roofing", "Owner", "roofing", "Austin", "US", "verified"),
            ("b@bolt.example", "Bo", "Bolt Electric", "Founder", "electrical", "Tulsa", "US", "valid"),
            ("c@cedar.example", "Cy", "Cedar Plumbing", "President", "plumbing", "Boise", "US", "verified"),
            ("A@acme.example", "Ann", "Acme Roofing", "Owner", "roofing", "Austin", "US", "verified"),   # repeat
            ("d@dune.example", "Di", "Dune Solar", "Owner", "solar", "Reno", "US", "catch-all"),         # not verified
            ("not-an-address", "Ed", "Elm Glass", "Owner", "glass", "Erie", "US", "verified"),           # bad
            ("f@fir.example", "Flo", "Fir Paint", "Intern", "paint", "Fargo", "US", "verified"),         # off audience (title)
            ("g@gum.example", "Gus", "Gum Tile", "Owner", "tile", "Perth", "AU", "verified"),            # off audience (country)
            ("h@hay.example", "Hal", "Hay Fence", "Owner", "fencing", "", "US", "verified")]             # blank city (fallback needs it)
    lst = d / "list.csv"
    with lst.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["Email", "first_name", "company", "title", "industry", "city", "country", "verified"]); w.writerows(rows)
    seen_prompt = d / "prompt.txt"

    def run(args, env=None):
        e = {**os.environ, "BOT_HOME": str(home), "PATH": f"{bins}:/usr/bin:/bin", "ROUTE_PY": str(pack / "route.py"), "FAKE_SEEN": str(seen_prompt), **(env or {})}
        return subprocess.run([sys.executable, COLD] + args, capture_output=True, text=True, env=e)

    r = run(["plan", "--settings", str(sett)])
    check("plan: 1,000 a day at 10 an inbox is 100 inboxes, 34 domains, 334 new contacts", "100 warmed inboxes" in r.stdout and "34 domains" in r.stdout and "334 new" in r.stdout, r.stdout + r.stderr)
    check("plan: 60 warmed inboxes is short (exit 1)", run(["plan", "--settings", str(sett), "--inboxes", "60"]).returncode == 1)
    over = d / "over.json"; over.write_text(json.dumps({**s, "per_inbox_a_day": 25}))
    check("more than 10 an inbox is held", run(["plan", "--settings", str(over)]).returncode == 1)

    nocol = d / "nocol.csv"; nocol.write_text("email,first_name,company,verified\na@x.example,A,X,verified\n")
    r = run(["match", "--settings", str(sett), "--campaign", "example-owners", "--list", str(nocol)])
    check("match: a list missing a column the campaign uses is held whole", r.returncode == 1 and "no column" in r.stdout and not (home / "cold").exists(), r.stdout)
    r = run(["match", "--settings", str(sett), "--campaign", "example-owners", "--list", str(lst)])
    want = ("rows 9", "bad_email 1", "not_verified 1", "repeat 1", "blank 1", "off_audience 2", "kept 3")
    check("match: each row kept or counted under its reason", all(x in r.stdout for x in want), r.stdout + r.stderr)
    check("match: says what share of the list fits, and holds nothing for it", r.returncode == 0 and "33% of this list fits" in r.stdout, r.stdout)
    check("match: prints no address", "@" not in r.stdout)
    ready = home / "cold" / "ready" / "example-owners.csv"
    check("match: the ready file is private", ready.exists() and stat.S_IMODE(ready.stat().st_mode) == 0o600)
    r = run(["match", "--settings", str(sett), "--campaign", "example-owners", "--list", str(lst)])
    check("match: the same list again keeps nothing new", "kept 0" in r.stdout and len(list(csv.DictReader(ready.open()))) == 3, r.stdout)

    r = run(["first-lines", "--settings", str(sett), "--campaign", "example-owners"])
    got = {x["company"]: x for x in csv.DictReader(ready.open())}
    check("first lines: a good line is kept, from codex", got["Acme Roofing"]["line_source"] == "codex" and "Austin" in got["Acme Roofing"]["first_line"], r.stdout + r.stderr)
    check("first lines: a line is tidied, not judged", got["Bolt Electric"]["first_line"] == "Bolt Electric wires homes in Tulsa." and got["Bolt Electric"]["line_source"] == "codex")
    check("first lines: an empty line gets the fallback, filled from the row", got["Cedar Plumbing"]["first_line"] == "I came across Cedar Plumbing while looking at plumbing businesses in Boise.")
    sent = seen_prompt.read_text()
    check("first lines: no address or name goes to the engine", "@" not in sent and "Ann" not in sent)
    check("first lines: the settings' model is passed to Codex", sent.endswith("MODEL=model-x"))
    r = run(["first-lines", "--settings", str(sett), "--campaign", "example-owners"])
    check("first lines: a rerun writes nothing again", "rows 0" in r.stdout)

    for x in ready.parent.glob("*.csv"):
        x.unlink()
    (home / "state" / "cold-email" / "seen.json").unlink()
    run(["match", "--settings", str(sett), "--campaign", "example-owners", "--list", str(lst)])
    r = run(["first-lines", "--settings", str(sett), "--campaign", "example-owners"], {"ROUTE_PY": str(BUILD / "engines" / "route.py")})
    got = list(csv.DictReader(ready.open()))
    check("first lines: with today's agent map no engine answers, and every row still gets a line", r.returncode == 0 and all(x["line_source"] == "fallback" and x["first_line"] for x in got), r.stdout + r.stderr)

    st = d / "stats.json"
    st.write_text(json.dumps({"example-owners": {"sent_today": 1000, "sent": 9000, "contacted": 3000, "replied": 330, "booked": 33, "bounced": 40}}))
    r = run(["read", "--settings", str(sett), "--stats", str(st)])
    check("read: on volume and on target is clean", r.returncode == 0 and "FLAG" not in r.stdout, r.stdout + r.stderr)
    st.write_text(json.dumps({"example-owners": {"sent_today": 600, "sent": 9000, "contacted": 3000, "replied": 90, "booked": 6, "bounced": 270}}))
    r = run(["read", "--settings", str(sett), "--stats", str(st)])
    check("read: under volume, under both targets and at the bounce line are each named", r.returncode == 1 and all(x in r.stdout for x in ("under volume", "reply rate 3.0%", "booking rate 0.2%", "PAUSE")), r.stdout)
    st.write_text("{}")
    check("read: a campaign with no stats is flagged", run(["read", "--settings", str(sett), "--stats", str(st)]).returncode == 1)
    for x in ready.parent.glob("*.csv"):
        x.unlink()
    (home / "state" / "cold-email" / "seen.json").unlink()
    run(["match", "--settings", str(blank), "--campaign", "example-owners", "--list", str(lst)])
    r = run(["first-lines", "--settings", str(blank), "--campaign", "example-owners"])
    check("a blank charter holds nothing: the list is matched and lines are written", r.returncode == 0 and "codex 2" in r.stdout, r.stdout + r.stderr)
    check("every run left its counts in the log", len(list((home / "log").glob("cold-email-*.jsonl"))) == 1)

print(f"\n{n - len(fails)} of {n} passed")
for f in fails:
    print("FAIL " + f)
sys.exit(1 if fails else 0)
