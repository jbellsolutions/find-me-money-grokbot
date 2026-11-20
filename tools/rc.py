#!/usr/bin/env python3
"""Operator CLI for the site's admin API. Standard library only.

Needs RC_SITE (e.g. https://findreferralpartners.com) and RC_ADMIN_KEY, from the environment or from
.secrets/fmm.env or .secrets/site.env in the bot's workspace (KEY=value lines).

  rc.py stats
  rc.py signups [--status new] [--area austin] [--since 2026-11-18T00:00:00Z] [--csv FILE]
  rc.py signup-set <id> [--status new|listed|matched|spam|paused] [--notes TEXT]
  rc.py list <signup id> [--blurb "One line about the business"]
  rc.py listings | listing-set <id> [--blurb T] [--wants T] | unlist <listing id>
  rc.py connections | connection-set <id> --status new|introduced|declined|spam
  rc.py removals | remove <email>
  rc.py matches | match <signup a> <signup b> [--notes T] | match-set <id> [--status S] [--notes T]
  rc.py pages | page-get <slug> | page-put <slug> --title T --description D --html FILE [--publish] | page-delete <slug>
"""
import argparse, json, os, sys, urllib.error, urllib.parse, urllib.request


def call(method, path, body=None, raw=False):
    here = os.path.dirname(os.path.abspath(__file__))
    for f in (os.path.join(os.getcwd(), ".secrets", "site.env"), os.path.join(os.getcwd(), ".secrets", "fmm.env"), os.path.join(here, "..", "..", ".secrets", "fmm.env"), os.path.join(here, "..", "..", ".secrets", "site.env"), os.path.join(here, "..", ".env.local")):
        if os.path.exists(f):  # KEY=value lines; the environment wins
            for line in open(f):
                k, _, v = line.strip().partition("=")
                if k in ("RC_SITE", "RC_ADMIN_KEY") and v and k not in os.environ:
                    os.environ[k] = v.strip().strip('"')
    site, key = os.environ.get("RC_SITE", "").rstrip("/"), os.environ.get("RC_ADMIN_KEY", "")
    if not site or not key:
        sys.exit("Set RC_SITE and RC_ADMIN_KEY (environment, or .secrets/site.env in the workspace).")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(site + "/admin" + path, data=data, method=method,
                                 headers={"authorization": "Bearer " + key, "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            t = r.read().decode()
            return t if raw else json.loads(t)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}")


def show(x):
    print(json.dumps(x, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd"); ap.add_argument("args", nargs="*")
    for f in ("status", "area", "since", "csv", "notes", "blurb", "wants", "title", "description", "html"):
        ap.add_argument("--" + f)
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args(); c, x = a.cmd, a.args
    pick = lambda *ks: {k: getattr(a, k) for k in ks if getattr(a, k) is not None}
    if c == "stats": show(call("GET", "/stats"))
    elif c == "signups":
        qs = urllib.parse.urlencode({**pick("status", "area", "since"), **({"format": "csv"} if a.csv else {})})
        if a.csv:
            open(a.csv, "w").write(call("GET", "/signups?" + qs, raw=True)); print("wrote", a.csv)
        else: show(call("GET", "/signups?" + qs))
    elif c == "signup-set": show(call("PATCH", f"/signups/{x[0]}", pick("status", "notes")))
    elif c == "list": show(call("POST", "/listings", {"signup_id": int(x[0]), **pick("blurb")}))
    elif c == "listings": show(call("GET", "/listings"))
    elif c == "listing-set": show(call("PATCH", f"/listings/{x[0]}", pick("blurb", "wants")))
    elif c == "unlist": show(call("DELETE", f"/listings/{x[0]}"))
    elif c == "connections": show(call("GET", "/connections"))
    elif c == "connection-set": show(call("PATCH", f"/connections/{x[0]}", pick("status")))
    elif c == "removals": show(call("GET", "/removals"))
    elif c == "remove": show(call("POST", "/remove", {"email": x[0]}))
    elif c == "matches": show(call("GET", "/matches"))
    elif c == "match": show(call("POST", "/matches", {"a_signup": int(x[0]), "b_signup": int(x[1]), **pick("notes")}))
    elif c == "match-set": show(call("PATCH", f"/matches/{x[0]}", pick("status", "notes")))
    elif c == "pages": show(call("GET", "/pages"))
    elif c == "page-get": show(call("GET", f"/pages/{x[0]}"))
    elif c == "page-put":
        show(call("PUT", f"/pages/{x[0]}", {"title": a.title, "description": a.description, "body_html": open(a.html).read(), "published": a.publish}))
    elif c == "page-delete": show(call("DELETE", f"/pages/{x[0]}"))
    else: sys.exit("Unknown command. Run with -h.")


if __name__ == "__main__":
    main()
