#!/usr/bin/env python3
"""GoHighLevel, for the CRM job: contacts, pipelines, opportunities, notes, tasks, tags and workflows. Standard library only.

Reads (need only the key):
    ghl.py check                                   the sub-account's name: proves the key reads
    ghl.py pipelines                               every pipeline and stage, with ids
    ghl.py contacts "<query>" [--limit N]          search contacts
    ghl.py contact <contactId>
    ghl.py opps [--pipeline ID] [--stage ID] [--contact ID] [--limit N]
    ghl.py workflows                               every workflow, with id and status

Writes (each asks the switches first; see below):
    ghl.py upsert --email E [--phone P] [--first F] [--last L] [--company C] [--tags a,b] [--source S]
    ghl.py tag <contactId> a,b
    ghl.py note <contactId> "<text>"
    ghl.py task <contactId> --title T [--due 2026-12-01T15:00:00Z] [--body B]
    ghl.py opp-new --contact ID --pipeline ID --stage ID --name N [--value USD]
    ghl.py opp-move <oppId> --stage ID [--status open|won|lost|abandoned]
    ghl.py workflow-add <contactId> <workflowId>   puts a person in a workflow, which can message them

Needs GHL_API_KEY (a Private Integration Token) and GHL_LOCATION_ID (the sub-account id), from the environment or a
KEY=value line in <workspace>/.secrets/*.env. There is no default sub-account: with none set, every command stops.

The switches. A write goes to GoHighLevel only when all of these hold: context/owners.md says `gohighlevel: bot`,
context/routines-on.md says `CRM: on` and `crm-writes: on`, and there is no context/STOP. workflow-add also needs
`ghl_workflow_enroll: auto` in context/standing-approvals.md, because a workflow can send. Otherwise the write is not
made: the exact command is added to requests/justin/crm-proposals-<date>.md and the script prints PROPOSED. So the CRM
job can run in full from the first day, and Justin sees what it would have written.

Never written, whatever the switches say: a Social Security number, a date of birth, a bank or card number, a full EIN,
a credit score. A payload that looks like one is refused."""
import argparse, datetime, json, os, pathlib, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
WS = pathlib.Path(os.environ.get("BOT_HOME") or (REPO.parent if REPO.name == "repo" else REPO))
API = "https://services.leadconnectorhq.com"
NEVER = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b(?:\d[ -]?){13,16}\b|\b\d{2}-\d{7}\b|\b(?:ssn|social security|date of birth|dob|routing number|credit score|fico)\b", re.I)


def setting(name):
    if os.environ.get(name):
        return os.environ[name]
    sec = WS / ".secrets"
    for f in sorted(sec.glob("*.env")) if sec.is_dir() else []:
        for l in f.read_text(errors="ignore").splitlines():
            k, _, v = l.strip().partition("=")
            if k == name and v:
                return v.strip().strip('"')
    return ""


def call(method, path, body=None, query=None):
    key = setting("GHL_API_KEY")
    if not key:
        sys.exit("Set GHL_API_KEY and GHL_LOCATION_ID (hidden prompt; they go in the workspace's .secrets/ file).")
    url = API + path + ("?" + urllib.parse.urlencode({k: v for k, v in query.items() if v}) if query else "")
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Authorization": "Bearer " + key, "Version": "2021-07-28", "Accept": "application/json",
                                          "Content-Type": "application/json", "User-Agent": "find-me-money-bot/1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            t = r.read().decode()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}")
    except urllib.error.URLError as e:
        sys.exit(f"{method} {path} -> no answer: {e.reason}")


def loc():
    v = setting("GHL_LOCATION_ID")
    if not v:
        sys.exit("Set GHL_LOCATION_ID: the sub-account this bot works in. There is no default.")
    return v


def lid():
    """The sub-account for a write: a write with none set is saved as a proposal, not stopped."""
    return setting("GHL_LOCATION_ID") or "?"


def guard(script, *args):
    r = subprocess.run([sys.executable, str(REPO / "guards" / "scripts" / script), *args], capture_output=True, text=True, env=dict(os.environ, BOT_HOME=str(WS)))
    return r.returncode == 0, (r.stdout.strip().splitlines() or ["?"])[-1]


def line(name, key):
    f = WS / "context" / name
    for l in f.read_text(errors="ignore").splitlines() if f.exists() else []:
        if re.match(rf"\s*{re.escape(key)}\s*:", l, re.I):
            return l.split(":", 1)[1].strip().lower()
    return ""


def may_write(sends=False):
    ok, said = guard("owner_guard.py", "check", "gohighlevel", "--routine", "CRM")
    if not ok:
        return f"owner guard says {said}"
    if line("routines-on.md", "crm-writes") != "on":
        return "crm-writes is not on"
    if sends:
        ok, said = guard("send_guard.py", "ghl_workflow_enroll", "--routine", "CRM")
        if not ok:
            return f"send guard says {said} for ghl_workflow_enroll"
    return ""


def write(method, path, body, sends=False):
    blob = json.dumps(body)
    if NEVER.search(blob):
        sys.exit("REFUSED: this looks like an SSN, a date of birth, a bank or card number, an EIN or a credit score. None of those go in the CRM.")
    why = may_write(sends) or ("the CRM's key or sub-account id is not set" if not (setting("GHL_API_KEY") and setting("GHL_LOCATION_ID")) else "")
    if why:
        d = WS / "requests" / "justin"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"crm-proposals-{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d}.md"
        if not f.exists():
            f.write_text("# CRM writes the bot would have made\n\nNot written, because a switch is off. Each line is the exact command.\n\n")
        with f.open("a") as h:
            h.write("- `python3 repo/tools/ghl.py " + " ".join(a if re.fullmatch(r"[\w@.:/,+-]+", a) else json.dumps(a) for a in sys.argv[1:]) + f"`  ({why})\n")
        print(f"PROPOSED, not written ({why}): {f}")
        return None
    out = call(method, path, body)
    print(json.dumps(out, indent=1)[:4000])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd"); ap.add_argument("args", nargs="*")
    for f in ("limit", "pipeline", "stage", "contact", "email", "phone", "first", "last", "company", "tags", "source", "title", "due", "body", "name", "value", "status"):
        ap.add_argument("--" + f)
    a = ap.parse_args(); c, x = a.cmd, a.args
    show = lambda o: print(json.dumps(o, indent=1)[:12000])
    if c == "check":
        o = call("GET", f"/locations/{loc()}")
        print("ok:", (o.get("location") or o).get("name", "?"))
    elif c == "pipelines":
        for p in call("GET", "/opportunities/pipelines", query={"locationId": loc()}).get("pipelines", []):
            print(f"{p['id']}  {p['name']}")
            for s in p.get("stages", []):
                print(f"    {s['id']}  {s['name']}")
    elif c == "contacts":
        show(call("POST", "/contacts/search", {"locationId": loc(), "pageLimit": int(a.limit or 20), **({"query": x[0]} if x else {})}))
    elif c == "contact":
        show(call("GET", f"/contacts/{x[0]}"))
    elif c == "opps":
        show(call("GET", "/opportunities/search", query={"location_id": loc(), "pipeline_id": a.pipeline, "pipeline_stage_id": a.stage, "contact_id": a.contact, "limit": a.limit or "50"}))
    elif c == "workflows":
        for w in call("GET", "/workflows/", query={"locationId": loc()}).get("workflows", []):
            print(f"{w['id']}  {w.get('status', '?'):10} {w['name']}")
    elif c == "upsert":
        if not (a.email or a.phone):
            sys.exit("upsert needs --email or --phone")
        b = {"locationId": lid(), "email": a.email, "phone": a.phone, "firstName": a.first, "lastName": a.last, "companyName": a.company,
             "source": a.source, "tags": [t.strip() for t in (a.tags or "").split(",") if t.strip()] or None}
        write("POST", "/contacts/upsert", {k: v for k, v in b.items() if v})
    elif c == "tag":
        write("POST", f"/contacts/{x[0]}/tags", {"tags": [t.strip() for t in x[1].split(",") if t.strip()]})
    elif c == "note":
        write("POST", f"/contacts/{x[0]}/notes", {"body": x[1]})
    elif c == "task":
        write("POST", f"/contacts/{x[0]}/tasks", {k: v for k, v in {"title": a.title, "body": a.body, "dueDate": a.due, "completed": False}.items() if v is not None})
    elif c == "opp-new":
        b = {"locationId": lid(), "contactId": a.contact, "pipelineId": a.pipeline, "pipelineStageId": a.stage, "name": a.name, "status": "open",
             "monetaryValue": float(a.value) if a.value else None}
        write("POST", "/opportunities/", {k: v for k, v in b.items() if v is not None})
    elif c == "opp-move":
        write("PUT", f"/opportunities/{x[0]}", {k: v for k, v in {"pipelineStageId": a.stage, "status": a.status}.items() if v})
    elif c == "workflow-add":
        write("POST", f"/contacts/{x[0]}/workflow/{x[1]}", {}, sends=True)
    else:
        sys.exit("Unknown command. Run with -h.")


if __name__ == "__main__":
    main()
