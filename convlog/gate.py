#!/usr/bin/env python3
"""The gate hook: one command per step of a send gate, for a pack whose gate is prose the bot follows, not code.

    gate.py drafted  <item> [--agent A]            the draft exists: log it before approval is asked
    gate.py approved <item> [--agent A]            the approver said yes to this exact item
    gate.py check    <item>                        exit 0 only if this item's text is in the log as drafted or approved
    gate.py sent|skipped|failed <item> [--row R]   the outcome, once the sending tool has confirmed it
    gate.py inbound --person P --text-file F [--channel email] [--agent sales-crm] [--subject S]
    gate.py day                                    the day's file, every line marked handed over, then the audit. Exit 1 if the
                                                   audit names a line
                                                   (a computer with no time zone data would lose part of the working day)

Exit codes: only check and day can fail. drafted, approved, sent, skipped, failed and inbound always exit 0 and print a
WARNING line if the log could not be written: a bot that sees a failure after a send may send again, and a missing log
line is the smaller harm. The daily audit catches it.
The workspace is BOT_HOME if set, else two folders above this script's folder (a pack lives at <workspace>/repo/).

An item is the file both client packs already use: ITEM:, ROLE: (or BOT:), then ---PAYLOAD--- with TO:, SUBJECT:, TEXT: and ---END---.
An id starting test- is logged as a test. A list item (TO names a file) is logged under wave-<id> until each row's outcome,
which is logged under that row's recipient.

Two hashes, two jobs: a pack's own approval hash covers every byte of the payload (recipients, subject and text) and
proves the approver saw exactly this. The log's hash covers the text alone, whitespace flattened, and only links a send
to its draft. This hook hashes TEXT for the log; it never replaces the pack's approval check."""
import os, pathlib, re, subprocess, sys, tempfile

CONV = str(pathlib.Path(__file__).resolve().parent / "convlog.py")


def parse(item):
    t = pathlib.Path(item).read_text(encoding="utf-8")
    m = re.search(r"^---PAYLOAD---\n(.*?)^---END---$", t, re.S | re.M)
    if not m:
        raise SystemExit(f"held: {item} has no ---PAYLOAD--- ... ---END--- block")
    pay = m.group(1)
    g = lambda pat, src=t: (re.search(pat, src, re.M) or [None, ""])[1].strip()
    text = re.search(r"^TEXT:\n(.*)", pay, re.S | re.M)
    return {"id": g(r"^ITEM:\s*(\S+)"), "role": g(r"^ROLE:\s*(\S+)") or g(r"^BOT:\s*(\S+)"), "to": g(r"^TO:\s*(.+)$", pay), "subject": g(r"^SUBJECT:\s*(.+)$", pay),
            "text": text.group(1) if text else pay}


ENV = {**os.environ, "BOT_HOME": os.environ.get("BOT_HOME") or str(pathlib.Path(__file__).resolve().parents[2])}


def conv(args, capture=False):
    return subprocess.run([sys.executable, CONV] + args, capture_output=capture, text=True, env=ENV)


def soft(args):
    """A logging step never fails the gate: warn and carry on."""
    try:
        r = conv(args, capture=True)
        if r.returncode != 0:
            print(f"WARNING: the conversation log did not take this line ({(r.stdout + r.stderr).strip()[:160]}). Put this warning in the daily note.")
        else:
            print(f"logged {r.stdout.strip()}")
    except OSError as e:
        print(f"WARNING: the conversation log could not be run ({e}). Put this warning in the daily note.")
    return 0


def main(a):
    if not a:
        print(__doc__); return 2
    step = a[0]
    opt = lambda k, d="": a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    if step == "day":
        d = conv(["daily", "--mark"], capture=True)
        print(d.stdout.strip())
        au = conv(["audit"], capture=True)
        print(au.stdout.strip())
        return 1 if (d.returncode or au.returncode) else 0
    if step == "inbound":
        if not (opt("--person") and opt("--text-file")):
            print("inbound needs --person and --text-file"); return 2
        return soft(["add", "--agent", opt("--agent", "sales-crm"), "--channel", opt("--channel", "email"), "--direction", "in", "--person", opt("--person"),
                     "--text-file", opt("--text-file"), "--subject", opt("--subject")])
    if step not in ("drafted", "approved", "check", "sent", "skipped", "failed") or len(a) < 2:
        print(__doc__); return 2
    it = parse(a[1])
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(it["text"])
    try:
        if step == "check":
            import hashlib
            return conv(["has-draft", hashlib.sha256(" ".join(it["text"].split()).encode()).hexdigest()]).returncode
        is_list = bool(re.search(r"sha256=|\.(csv|txt|json)\b", it["to"]))
        person = opt("--row") or (f"wave-{it['id']}" if is_list else it["to"].split(",")[0].strip() or "unknown")
        return soft(["add", "--agent", opt("--agent", it["role"] or "unknown"), "--channel", opt("--channel", "email"), "--direction", "out", "--status", step,
                     "--person", person, "--text-file", f.name, "--approval", it["id"], "--subject", it["subject"]]
                    + (["--test"] if it["id"].startswith("test-") else []))
    finally:
        os.unlink(f.name)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
