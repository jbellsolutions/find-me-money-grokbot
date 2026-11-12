#!/usr/bin/env python3
"""muse.py - drive Meta's Muse Mac app on an Orgo computer, built on orgo.py.

Every keystroke goes through macOS System Events after `activate`, because
Orgo's own `key` endpoint takes X11 names and does not send Cmd shortcuts on
macOS. Clicks go through Orgo (absolute pixels, 1920x1080 at scale 1) and are
given here RELATIVE to the Muse main window, which `pin` puts at a fixed place.

Usage (run from anywhere; the Orgo computer is $MUSE_COMPUTER, set at intake; no default):
  muse.py pin                       # activate Muse, put main window at 587,30 size 1200x800
  muse.py state                     # windows, frontmost app, Muse running, RAM
  muse.py shot  [-o f.png] [--scale 0.5]
  muse.py nav   chat|search|feed|ideas|goals|library|new|menu|settings|shortcuts|sysfiles|activity|status|latest
  muse.py open-chat "<side chat title>"   # via Cmd+K search palette
  muse.py read  [-o out.txt] [--tail N]   # select-all + copy of the focused view, clipboard restored
  muse.py pagedown [N] | pageup [N]       # scroll the web view (wheel scroll does not work)
  muse.py key   "<keystroke spec>"         # e.g. cmd+k, return, pagedown. ESCAPE STOPS A RUNNING MUSE RESPONSE
  muse.py click RX RY [--double]           # relative to the pinned window's top-left
  muse.py settings [--tab permissions|data-controls|...] [--connector facebook|instagram|...]
  muse.py ask   "<prompt>" --yes-send-to-muse [--marker ID]  # paste into composer and press Return
  muse.py wait-marker ID [--timeout 900]   # poll the open chat until END-ID appears; print the block
Writes NOTHING to Facebook/Instagram itself. `ask` only sends a chat message to Muse;
the prompt must forbid posting/commenting/DMs. Approval cards are never clicked.
"""
import argparse, base64, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ORGO = os.environ.get("ORGO_PY") or next((p for p in [
    os.path.join(HERE, "..", "..", "..", "..", "orgo-computer-use", "scripts", "orgo.py"),
    os.path.expanduser("/workspace/find-me-money/repo/skills/muse/orgo-computer-use/scripts/orgo.py"),
    os.path.expanduser("/workspace/find-me-money/repo/skills/muse/orgo-computer-use/scripts/orgo.py"),
] if os.path.exists(p)), None)
COMPUTER = os.environ.get("MUSE_COMPUTER", "").strip()


def _never_touch():
    """The private never-touch list: env NEVER_TOUCH (comma-separated), else <workspace>/.secrets/never-touch.txt.
    None when missing or empty. The workspace is BOT_HOME, else the folder above repo/."""
    raw = os.environ.get("NEVER_TOUCH", "")
    names = raw.split(",")
    if not raw.strip():
        ws = os.environ.get("BOT_HOME") or os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
        try:
            names = [l.split("#", 1)[0] for l in open(os.path.join(ws, ".secrets", "never-touch.txt"), errors="ignore")]
        except OSError:
            names = []
    out = {n.strip().lower() for n in names if n.strip()}
    return out or None


def _guard():
    """Fail closed: no computer named, no never-touch list, or a listed computer, and nothing runs (not even a read)."""
    if not COMPUTER:
        raise SystemExit("refused: MUSE_COMPUTER is not set (intake)")
    nt = _never_touch()
    if nt is None:
        raise SystemExit("refused: no never-touch list (set NEVER_TOUCH or .secrets/never-touch.txt at intake)")
    if any(n == COMPUTER.lower() or n in COMPUTER.lower() for n in nt):
        raise SystemExit("refused: MUSE_COMPUTER is on the never-touch list")

WIN_X, WIN_Y, WIN_W, WIN_H = 587, 30, 1200, 800
# Left rail, relative to window origin (x=39).
RAIL = {"chat": (39, 212), "search": (39, 268), "feed": (39, 324), "ideas": (39, 380),
        "goals": (39, 436), "library": (39, 492), "new": (39, 564), "menu": (39, 766)}
SYSFILES = (163, 763)  # "System files" at the bottom of the Library column
COMPOSER = (700, 755)  # message box text area
NEWSIDE = (289, 114)   # "+" next to "Side chats"
NEUTRAL = (39, 660)    # empty gap in the left rail between "+" and the menu: never a chat row, never Call/Invite

KEYCODES = {"escape": 53, "return": 36, "enter": 36, "tab": 48, "pagedown": 121, "pageup": 116,
            "end": 119, "home": 115, "down": 125, "up": 126, "left": 123, "right": 124, "delete": 51}


def orgo(*args, check=True, capture=True):
    _guard()
    if not ORGO:
        sys.exit("orgo.py not found; set ORGO_PY")
    r = subprocess.run([sys.executable, ORGO, *args], capture_output=capture, text=True)
    if check and r.returncode != 0:
        sys.exit(f"orgo {args[0]} failed: {r.stdout}{r.stderr}")
    return r.stdout


def mac(script, timeout=120):
    """Run a bash script on the Mac (sent base64 so quoting is safe)."""
    b = base64.b64encode(script.encode()).decode()
    return orgo("bash", COMPUTER, f"echo {b} | base64 -D | bash", "--timeout", str(timeout), check=False)


def osa(lines):
    """AppleScript lines -> one osascript call, Muse activated first."""
    body = "\n".join(['tell application "Muse" to activate', "delay 0.4", *lines])
    b = base64.b64encode(body.encode()).decode()
    return mac(f"echo {b} | base64 -D | osascript 2>&1")


def keystroke_lines(spec):
    parts = spec.lower().split("+")
    key, mods = parts[-1], parts[:-1]
    m = {"cmd": "command down", "command": "command down", "shift": "shift down",
         "alt": "option down", "option": "option down", "ctrl": "control down", "control": "control down"}
    using = ", ".join(m[x] for x in mods)
    using = (" using {" + using + "}") if using else ""
    if key in KEYCODES:
        return [f'tell application "System Events" to key code {KEYCODES[key]}{using}']
    return [f'tell application "System Events" to keystroke "{key}"{using}']


def click_rel(rx, ry, double=False):
    args = ["click", COMPUTER, str(WIN_X + rx), str(WIN_Y + ry)] + (["--double"] if double else [])
    orgo(*args)


def cmd_pin(a):
    print(osa([
        'tell application "System Events" to tell process "Muse"',
        f"  set position of window 1 to {{{WIN_X}, {WIN_Y}}}",
        f"  set size of window 1 to {{{WIN_W}, {WIN_H}}}",
        '  return (name of every window as string) & " | " & (position of window 1 as string) & " | " & (size of window 1 as string)',
        "end tell"]).strip())


def cmd_state(a):
    print(mac(r'''
pgrep -x Muse >/dev/null && echo "Muse: running (pid $(pgrep -x Muse))" || echo "Muse: NOT running"
osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>&1 | sed 's/^/frontmost: /'
osascript -e 'tell application "System Events" to tell process "Muse" to get {name, position, size} of every window' 2>&1 | sed 's/^/windows: /'
memory_pressure | grep -i "free percentage" ; sysctl -n hw.memsize | awk '{print "RAM GB:", $1/1073741824}'
'''))


def cmd_shot(a):
    out = a.o or f"muse-{int(time.time())}.png"
    print(orgo("screenshot", COMPUTER, "-o", out, "--scale", str(a.scale)).strip())


def cmd_key(a):
    print(osa(keystroke_lines(a.spec)).strip())


def cmd_nav(a):
    t = a.target
    if t == "settings":
        return print(osa(keystroke_lines("cmd+,")).strip() or "settings window opened (close with: key cmd+w)")
    if t in ("activity", "status", "latest"):
        # slash command typed into the (empty) composer: opens a panel / view, sends nothing to Meta.
        # No Escape: Escape STOPS a running Muse response.
        click_rel(*COMPOSER); time.sleep(0.5)
        return print(osa(["delay 0.2",
            'tell application "System Events" to keystroke "/%s"' % t, "delay 0.9"] + keystroke_lines("return")).strip() or f"/{t} run")
    if t == "shortcuts":
        return print(osa(keystroke_lines("cmd+/")).strip() or "shortcuts sheet (close with: key escape)")
    if t == "sysfiles":
        click_rel(*RAIL["library"]); time.sleep(2); click_rel(*SYSFILES)
    else:
        click_rel(*RAIL[t])
    time.sleep(2)
    print(f"nav {t}: ok (verify with shot)")


def read_script(tail):
    return r'''
SAVED=$(mktemp); pbpaste > "$SAVED" 2>/dev/null
printf "" | pbcopy
osascript -e 'tell application "Muse" to activate' -e 'delay 0.4' \
  -e 'tell application "System Events" to keystroke "a" using command down' -e 'delay 0.3' \
  -e 'tell application "System Events" to keystroke "c" using command down' >/dev/null 2>&1
sleep 0.8
OUT=$(pbpaste)
pbcopy < "$SAVED"; rm -f "$SAVED"
osascript -e 'tell application "System Events" to key code 124' >/dev/null 2>&1   # collapse selection
printf "%s" "$OUT" | ''' + (f"tail -c {tail}" if tail else "cat") + "\n"


def cmd_read(a):
    if not a.no_focus:
        click_rel(*NEUTRAL)  # a web-view click is the only reliable way to take focus off the composer
    txt = mac(read_script(a.tail), timeout=60)
    if a.o:
        open(a.o, "w").write(txt); print(f"{len(txt)} chars -> {a.o}")
    else:
        sys.stdout.write(txt)


def cmd_page(a, code):
    osa([f'tell application "System Events" to key code {code}'] * a.n)
    print("ok")


def cmd_click(a):
    click_rel(a.rx, a.ry, a.double); print("ok")


def cmd_open_chat(a):
    b = base64.b64encode(a.title.encode()).decode()
    osa(keystroke_lines("cmd+k") + ["delay 0.8"])   # no Escape: it stops a running response
    mac(f"echo {b} | base64 -D | pbcopy")
    osa(keystroke_lines("cmd+v") + ["delay 1.2"] + keystroke_lines("return"))
    time.sleep(2)
    print(f"opened '{a.title}' via Cmd+K (verify with shot)")


# Settings is its own window (Cmd+,). Absolute screen pixels, measured with Muse's main window pinned.
SETTINGS_TABS = {"general": 182, "connectors": 218, "computer-use": 254, "file-system": 290, "dictation": 326,
                 "wallet": 362, "secure-store": 398, "permissions": 434, "messaging": 470, "devices": 506,
                 "data-controls": 542, "voice": 578, "help": 614, "legal": 650}   # x = 870. "Log out" (y 698) is never clicked.
CONNECTED_TAB = (1419, 256)
CONNECTOR_VIEW_Y = {"browser": 328, "clickup": 377, "facebook": 426, "highlevel": 474, "instagram": 524,
                    "slack": 573, "threads": 622}   # x = 1525 on the Connected tab; order is alphabetical, re-check with shot
SETTINGS_BACK = (1041, 159)


def cmd_settings(a):
    osa(keystroke_lines("cmd+,") + ["delay 1.5"])
    geo = osa(['tell application "System Events" to tell process "Muse"',
               '  set position of window "Settings" to {787, 130}',
               '  return (position of window "Settings" as string) & "/" & (size of window "Settings" as string)',
               'end tell']).strip()
    if geo != "787130/800600":
        sys.exit(f"Settings window geometry is {geo!r}, expected 787130/800600: take a shot, click nothing blind")
    if a.tab:
        orgo("click", COMPUTER, "870", str(SETTINGS_TABS[a.tab])); time.sleep(2)
    if a.connector:
        orgo("click", COMPUTER, "870", str(SETTINGS_TABS["connectors"])); time.sleep(2)
        orgo("click", COMPUTER, *map(str, CONNECTED_TAB)); time.sleep(2)
        orgo("click", COMPUTER, "1525", str(CONNECTOR_VIEW_Y[a.connector])); time.sleep(3)
    print("settings open (read with: read --no-focus; page with: pagedown; close with: key cmd+w)")


def cmd_ask(a):
    if not a.yes_send_to_muse:
        sys.exit("ask sends a chat message to Muse. Re-run with --yes-send-to-muse.")
    prompt = a.prompt
    if a.marker:
        prompt += (f"\n\nFormat: start your final answer with the line BEGIN-{a.marker} and end it with "
                   f"the line END-{a.marker}. Put nothing after END-{a.marker}.")
    b = base64.b64encode(prompt.encode()).decode()
    if a.new_side_chat:
        click_rel(*NEWSIDE); time.sleep(2.5)
    mac(f"SAVED=$(mktemp); pbpaste > $SAVED; echo {b} | base64 -D | pbcopy; echo $SAVED > /tmp/.muse_clip")
    # Focus the composer by CLICKING it. Escape and Shift+Escape both throw away a fresh, empty side chat
    # (you land back in Main chat), and plain Escape also stops a running Muse response.
    click_rel(*COMPOSER); time.sleep(0.5)
    osa(["delay 0.2"] + keystroke_lines("cmd+v") + ["delay 0.8"] + keystroke_lines("return"))
    mac('S=$(cat /tmp/.muse_clip); pbcopy < "$S"; rm -f "$S" /tmp/.muse_clip')
    print("sent to Muse (verify with shot)")


def cmd_wait_marker(a):
    end = time.time() + a.timeout
    pat = re.compile(rf"BEGIN-{re.escape(a.id)}\s*\n(.*?)\nEND-{re.escape(a.id)}", re.S)
    while time.time() < end:
        click_rel(*NEUTRAL)
        txt = mac(read_script(60000), timeout=60)
        found = pat.findall(txt)
        # the prompt itself contains the marker words once each; a real answer adds a block with content
        found = [f for f in found if "Put nothing after" not in f and f.strip()]
        if found:
            print(found[-1]); return
        if re.search(r"\b(Allow|Deny|Don.t allow|Approve)\b", txt[-3000:]):
            print("NOTE: approval-like words in the newest text; take a screenshot. Never click it.", file=sys.stderr)
        time.sleep(a.every)
    sys.exit(f"timeout: no END-{a.id} block yet")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("pin").set_defaults(fn=cmd_pin)
    s.add_parser("state").set_defaults(fn=cmd_state)
    x = s.add_parser("shot"); x.add_argument("-o"); x.add_argument("--scale", type=float, default=0.5); x.set_defaults(fn=cmd_shot)
    x = s.add_parser("nav"); x.add_argument("target", choices=list(RAIL) + ["settings", "shortcuts", "sysfiles", "activity", "status", "latest"]); x.set_defaults(fn=cmd_nav)
    x = s.add_parser("open-chat"); x.add_argument("title"); x.set_defaults(fn=cmd_open_chat)
    x = s.add_parser("read"); x.add_argument("-o"); x.add_argument("--tail", type=int); x.add_argument("--no-focus", action="store_true", help="skip the focus click (Settings window, sheets, editors)"); x.set_defaults(fn=cmd_read)
    x = s.add_parser("pagedown"); x.add_argument("n", nargs="?", type=int, default=1); x.set_defaults(fn=lambda a: cmd_page(a, 121))
    x = s.add_parser("pageup"); x.add_argument("n", nargs="?", type=int, default=1); x.set_defaults(fn=lambda a: cmd_page(a, 116))
    x = s.add_parser("key"); x.add_argument("spec"); x.set_defaults(fn=cmd_key)
    x = s.add_parser("click"); x.add_argument("rx", type=int); x.add_argument("ry", type=int); x.add_argument("--double", action="store_true"); x.set_defaults(fn=cmd_click)
    x = s.add_parser("settings"); x.add_argument("--tab", choices=list(SETTINGS_TABS)); x.add_argument("--connector", choices=list(CONNECTOR_VIEW_Y)); x.set_defaults(fn=cmd_settings)
    x = s.add_parser("ask"); x.add_argument("prompt"); x.add_argument("--marker"); x.add_argument("--new-side-chat", action="store_true", help="click + (new side chat) first; the chat is created when the message sends"); x.add_argument("--yes-send-to-muse", action="store_true"); x.set_defaults(fn=cmd_ask)
    x = s.add_parser("wait-marker"); x.add_argument("id"); x.add_argument("--timeout", type=int, default=900); x.add_argument("--every", type=int, default=30); x.set_defaults(fn=cmd_wait_marker)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
