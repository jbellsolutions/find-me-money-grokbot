#!/usr/bin/env python3
"""The LinkedIn lane: which path an action takes, and the daily caps. No browser, no LinkedIn call: it only decides and queues.

    lane.py route <action>                 prints outflo, local or refuse, and why
    lane.py order <action> --person P --text-file F [--url U]
                                           queues one work order in $BOT_HOME/linkedin/orders/ if the path and today's cap allow
    lane.py counts                         today's orders per action against the caps
    lane.py stop "<what was seen>"         a warning, checkpoint or CAPTCHA: no more orders today, and the owner is told

Paths (LINKEDIN.md has the reasons):
    outflo   campaign work the LinkedIn tool does from its own per-profile connection: connection requests, sequences,
             first-degree messages, campaign replies.
    local    what the tool can't do: posts, comments, comment replies, reading the feed. Done on the owner's own
             computer, in the browser they already use, at a person's pace, or by the owner's own tap.
    refuse   anything from this computer. LINKEDIN_HOST must be absent or 'none' here: the GrokBot computer and the
             worker box are data-centre addresses and never sign in to LinkedIn.
Caps come from LINKEDIN_CAPS (JSON) or the defaults below; a campaign may lower them, never raise them past the
ceiling without the owner's dated words in context/standing-approvals.md."""
import datetime, hashlib, json, os, pathlib, sys

HOME = pathlib.Path(os.environ.get("BOT_HOME", "."))
Q = HOME / "linkedin" / "orders"
PATHS = {"connection_request": "outflo", "sequence_message": "outflo", "first_degree_message": "outflo", "campaign_reply": "outflo",
         "post": "local", "comment": "local", "comment_reply": "local", "dm_reply": "local", "read_feed": "local", "read_inbox": "local"}
DEFAULT_CAPS = {"connection_request": 20, "sequence_message": 50, "first_degree_message": 50, "campaign_reply": 50,
                "post": 1, "comment": 10, "comment_reply": 20, "dm_reply": 30, "read_feed": 6, "read_inbox": 6}


def caps():
    c = dict(DEFAULT_CAPS)
    for k, v in json.loads(os.environ.get("LINKEDIN_CAPS", "{}")).items():
        if k in c:
            c[k] = min(int(v), c[k])  # a campaign lowers a cap; raising one is the owner's edit to this file's ceiling
    return c


def today():
    return f"{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d}"


def counts():
    out = {}
    for f in Q.glob(f"{today()}-*.json"):
        a = json.loads(f.read_text())["action"]
        out[a] = out.get(a, 0) + 1
    return out


def main(a):
    if len(a) < 1:
        print(__doc__); return 2
    if a[0] == "counts":
        n, c = counts(), caps()
        for k in PATHS:
            print(f"{k:22} {n.get(k, 0):3} of {c[k]:3}  {PATHS[k]}")
        print("STOPPED today: " + (Q / f"{today()}.STOP").read_text() if (Q / f"{today()}.STOP").exists() else "not stopped"); return 0
    if a[0] == "stop":
        Q.mkdir(parents=True, exist_ok=True)
        (Q / f"{today()}.STOP").write_text(a[1] if len(a) > 1 else "stopped")
        j = HOME / "requests" / "justin"
        j.mkdir(parents=True, exist_ok=True)
        (j / f"linkedin-stop-{today()}.md").write_text(f"LinkedIn stopped for {today()}: {a[1] if len(a) > 1 else ''}\nNothing more is queued today. Say when it is safe to go on.\n")
        print("stopped for today; the owner's queue has the note"); return 0
    action = a[1] if len(a) > 1 else ""
    if action not in PATHS:
        print(f"refuse: '{action}' is not a LinkedIn action this lane knows ({', '.join(PATHS)})"); return 1
    if os.environ.get("LINKEDIN_HOST", "none") != "none":
        print("refuse: LINKEDIN_HOST is set on this computer. LinkedIn is never signed in on the GrokBot computer or a worker box"); return 1
    if a[0] == "route":
        print(f"{PATHS[action]}: {action}"); return 0
    if a[0] == "order":
        if (Q / f"{today()}.STOP").exists():
            print("held: LinkedIn is stopped for today"); return 1
        if counts().get(action, 0) >= caps()[action]:
            print(f"held: today's cap for {action} is {caps()[action]}"); return 1
        person = a[a.index("--person") + 1] if "--person" in a else ""
        text = pathlib.Path(a[a.index("--text-file") + 1]).read_text() if "--text-file" in a else ""
        if action not in ("read_feed", "read_inbox") and not (person and text.strip()):
            print("order needs --person and --text-file"); return 2
        h = hashlib.sha256(" ".join(text.split()).encode()).hexdigest()
        Q.mkdir(parents=True, exist_ok=True)
        oid = f"{today()}-{action}-{h[:10]}-{counts().get(action, 0) + 1}"
        (Q / f"{oid}.json").write_text(json.dumps({"id": oid, "action": action, "path": PATHS[action], "person": person, "sha256": h, "text": text,
                                                 "url": a[a.index('--url') + 1] if "--url" in a else "", "state": "queued"}, ensure_ascii=False, indent=1))
        print(f"queued for {PATHS[action]}: {oid}"); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
