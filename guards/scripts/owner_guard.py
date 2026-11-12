#!/usr/bin/env python3
"""Owner guard: the bot never writes what a live system already writes.

    owner_guard.py check <system> [--routine <NAME>] [--target <NAME>]   prints bot, live, stopped or refused; exit 0 only for bot
    owner_guard.py target <NAME>                        ok or refused: may the bot touch this computer, agent or account at all
    owner_guard.py list                                 every system and who writes it

Find Me Money may already run live systems that write on their own: the CRM, the Radar and its
lanes, the Lending Hub, Muse, the social sender, the cold-email sender and older agents. Two writers on one system double-post and double-file. So every
write to one of them asks this guard first.

The table is context/owners.md, one line per system: `<system>: live` or `<system>: bot`.
- `live` (the default, and what any system missing from the file gets): the live system owns the
  writes. The bot reads, drafts and queues a request in requests/justin/; it does not write.
- `bot`: Justin moved that system's writes to this bot (his words and the date go beside the line,
  and the live writer for it is paused first). Only then may the role that owns it write, and only
  through its other guards (send_guard, spend_guard, crm-writes: on).
A routine set to `test` in context/routines-on.md always gets `live`. context/STOP gives `stopped`.

The never-touch list (env NEVER_TOUCH, comma-separated, or .secrets/never-touch.txt in the workspace) names what the
bot never uses, not even to read. It is private and set at intake. With no list, every guarded write is `refused`
(fail closed); a `--target` on the list is `refused` too."""
import sys, re
from _ws import p, stopped, touch_refusal

# Live systems that already write on their own. The bot's own Slack channel, Notion pages and vault are not here:
# reporting is the bot's own and never waits on this guard.
# Extra systems can be added at intake (OWNER_SYSTEMS, comma-separated); any system not in context/owners.md is `live`.
import os
DEFAULTS = ["pinnacle-ghl", "funding-radar", "radar-cl", "fbgroups-lane", "lending-hub", "muse-app",
            "social-sender", "legacy-agent", "cold-email-sender",
            *[x.strip().lower() for x in os.environ.get("OWNER_SYSTEMS", "").split(",") if x.strip()]]


def table():
    f, out = p("context", "owners.md"), {}
    if f.exists():
        for l in f.read_text(errors="ignore").splitlines():
            m = re.match(r"\s*[-*]?\s*`?([a-z0-9][a-z0-9_-]*)`?\s*:\s*(bot|live)\b", l, re.I)
            if m:
                out[m.group(1).lower()] = m.group(2).lower()
    return out


def routine_mode(name):
    f = p("context", "routines-on.md")
    if not f.exists():
        return ""
    for l in f.read_text(errors="ignore").splitlines():
        if re.match(rf"\s*{re.escape(name)}\s*:", l, re.I):
            return l.split(":", 1)[1].strip().lower()
    return ""


def main(a):
    if a[:1] == ["list"]:
        t = table()
        for s in sorted(set(DEFAULTS) | set(t)):
            print(f"{s}: {t.get(s, 'live')}")
        return 0
    if len(a) >= 2 and a[0] == "target":
        why = touch_refusal(a[1])
        print(why or "ok"); return 1 if why else 0
    if len(a) >= 2 and a[0] == "check":
        system = a[1].lower()
        routine = a[a.index("--routine") + 1] if "--routine" in a else None
        target = a[a.index("--target") + 1] if "--target" in a else ""
        if stopped():
            print("stopped"); return 1
        why = touch_refusal(system, target)
        if why:
            print(why); return 1
        if routine and routine_mode(routine) != "on":
            print("live"); return 1
        who = table().get(system, "live")
        print(who)
        return 0 if who == "bot" else 1
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
