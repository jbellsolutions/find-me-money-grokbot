#!/usr/bin/env python3
"""orgo.py: connect to, run and control Orgo cloud computers, and drive the Hermes agents on them.

Standard library only (Python 3.8+). Talks to Orgo's REST API (https://www.orgo.ai/api) with
ORGO_API_KEY, so it runs anywhere: a Mac, a GrokBot bot's computer, a Hermes profile, CI.

  Computers
    orgo.py list [--json]                         every computer you can see, by workspace
    orgo.py get <computer> [--json]               one computer (credential fields removed)
    orgo.py status <computer>                     uptime, RAM, disk, OS, Hermes agents and profiles
    orgo.py start|stop|restart <computer> --yes   lifecycle (changes the computer: needs the owner's yes)

  Actions (computer use)
    orgo.py bash <computer> "<command>" [--timeout S] [--screen ID]
    orgo.py exec <computer> (--code "<python>" | --file f.py) [--timeout S]
    orgo.py push <computer> <local-dir> <remote-dir>   copy a folder onto the computer
    orgo.py screenshot <computer> [-o shot.png] [--scale 0.5] [--screen ID]
    orgo.py click <computer> X Y [--right] [--double]
    orgo.py type <computer> "<text>"
    orgo.py key <computer> "<key>"                Enter, Tab, ctrl+c, alt+F4 ...
    orgo.py scroll <computer> X Y [--up] [--amount N]
    orgo.py drag <computer> X1 Y1 X2 Y2
    orgo.py wait <computer> SECONDS

  Hermes on the computer
    orgo.py hermes agents <computer>
    orgo.py hermes ask <computer> "<message>" [--profile P] [--resume SID] [--max-turns N] [--timeout S] [--agent A]
    orgo.py hermes start <computer> (--message "<task>" | --file task.md) [--profile P] [--max-turns N]
    orgo.py hermes result <computer> <job-id>
    orgo.py hermes logs <computer> [N] [--profile P] [--file gateway|errors|agent]
    orgo.py hermes cron <computer> [--profile P]
    orgo.py hermes skill-install <computer> <skill-dir> --profile P --yes
    orgo.py hermes skill-rollback <computer> <skill-name> --profile P --yes

<computer> is an exact name, an id or id prefix, a unique substring of a name, or `local`
(run on this machine: use it when you are already on the target computer).

Every line that comes back is scrubbed for keys, tokens, JWTs, long hex/base64 runs and t.me links.
"""
import argparse
import base64
import io
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("ORGO_API_BASE", "https://www.orgo.ai/api").rstrip("/")
KEY = None
ENV_FILES = [os.path.expanduser(p) for p in ("~/.orgo/.env", "~/.hermes/.env", "./.env.local", "./.env")]
STRIP_FIELDS = {"vnc_password", "connection_url", "url", "owner_email", "instance_details", "hostname", "fly_instance_id", "instance_id"}

# --- secrets ------------------------------------------------------------------------------

SCRUB = [
    (re.compile(r"https?://t\.me/\S+"), "[t.me link]"),
    (re.compile(r"(?i)\bBearer\s+\S+"), "Bearer [REDACTED]"),
    (re.compile(r"\b(?:sk_live_|sk_test_|sk-ant-|sk-|xox[abposr]-|xapp-|ghp_|gho_|ghs_|ghu_|github_pat_|glpat-|AKIA|AIza)[A-Za-z0-9_\-]{8,}"), "[REDACTED]"),
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"), "[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[REDACTED-JWT]"),
    (re.compile(r"(?i)\b([A-Za-z0-9_]*(?:token|secret|password|passwd|api[_-]?key|apikey|access[_-]?key|private[_-]?key)[A-Za-z0-9_]*)"
                r"(\s*[\"']?\s*[=:]\s*[\"']?)([^\s\"',]{8,})"), r"\1\2[REDACTED]"),
    (re.compile(r"\b[A-Fa-f0-9]{40,}\b"), "[REDACTED-HEX]"),
    (re.compile(r"(?<![\w/.-])(?=[A-Za-z0-9+_-]*\d)(?=[A-Za-z0-9+_-]*[A-Za-z])[A-Za-z0-9+_-]{48,}={0,2}"), "[REDACTED-B64]"),
]


def scrub(text):
    if not text:
        return text
    if KEY:
        text = text.replace(KEY, "[REDACTED]")
    for pat, rep in SCRUB:
        text = pat.sub(rep, text)
    return text


def die(msg, code=1):
    print(scrub(str(msg)), file=sys.stderr)
    sys.exit(code)


def load_key(required=True):
    key = os.environ.get("ORGO_API_KEY")
    for path in ENV_FILES:
        if key:
            break
        if os.path.exists(path):
            # Read only the one line: sourcing a whole .env breaks on unquoted values.
            with open(path, errors="replace") as f:
                for line in f:
                    m = re.match(r"\s*(?:export\s+)?ORGO_API_KEY\s*=\s*(.*?)\s*$", line)
                    if m:
                        key = m.group(1).strip("\"'")
    if not key and required:
        die("ORGO_API_KEY is not set (environment, ~/.orgo/.env, ~/.hermes/.env, ./.env.local). Ask the owner for a workspace-scoped key.")
    return key


# --- REST -----------------------------------------------------------------------------------

def call(method, path, body=None, query=None, timeout=120, raw=False):
    url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": "orgo-computer-use/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
                return payload if raw else (json.loads(payload) if payload else {})
        except urllib.error.HTTPError as e:
            text = e.read().decode(errors="replace")
            if e.code in (429, 503, 504) and attempt < 3:
                time.sleep(int(e.headers.get("Retry-After") or 2 ** (attempt + 1)))
                continue
            die(f"Orgo API {method} {path} -> HTTP {e.code}: {text[:400]}", 2)
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            die(f"Orgo API unreachable ({e.reason})", 2)


def clean(rec):
    return {k: v for k, v in rec.items() if k not in STRIP_FIELDS}


def computers():
    out = []
    for ws in call("GET", "/workspaces").get("workspaces", []):
        for d in ws.get("desktops", []):
            d = clean(d)
            d["workspace_name"] = ws.get("name")
            d["workspace_id"] = ws.get("id")
            d["role"] = ws.get("role")
            out.append(d)
    return out


def never_touch():
    """The private never-touch list: env NEVER_TOUCH (comma-separated), else .secrets/never-touch.txt in the workspace
    (BOT_HOME, else the folder above repo/). None when missing or empty."""
    raw = os.environ.get("NEVER_TOUCH", "")
    names = raw.split(",")
    if not raw.strip():
        here = os.path.dirname(os.path.abspath(__file__))
        ws = os.environ.get("BOT_HOME") or os.path.abspath(os.path.join(here, "..", "..", "..", "..", ".."))
        try:
            with open(os.path.join(ws, ".secrets", "never-touch.txt"), errors="ignore") as f:
                names = [l.split("#", 1)[0] for l in f]
        except OSError:
            names = []
    out = {n.strip().lower() for n in names if n.strip()}
    return out or None


def guard_target(*names):
    """Fail closed before any computer is touched (a read can wake one): no never-touch list, or a match, refuses."""
    nt = never_touch()
    if nt is None:
        die("refused: no never-touch list (set NEVER_TOUCH or .secrets/never-touch.txt at intake)", 3)
    for name in names:
        t = (name or "").strip().lower()
        if t and any(n == t or n in t for n in nt):
            die("refused: that computer is on the never-touch list", 3)


def resolve(name):
    if name == "local":
        return {"id": "local", "name": "local", "os": sys.platform}
    guard_target(name)
    comps = computers()
    b = name.casefold()
    for test in (lambda c: (c.get("name") or "").casefold() == b,
                 lambda c: c["id"].startswith(name),
                 lambda c: b in (c.get("name") or "").casefold()):
        hits = [c for c in comps if test(c)]
        if len(hits) == 1:
            guard_target(hits[0].get("name"), hits[0].get("id"), hits[0].get("workspace_name"))
            return hits[0]
        if len(hits) > 1:
            die(f"'{name}' matches several computers: " + ", ".join(f"{c['name']} ({c['workspace_name']}, {c['id'][:8]})" for c in hits))
    die(f"no computer matches '{name}'. Known: " + ", ".join(sorted(c.get("name") or "?" for c in comps)))


def bash(comp, command, timeout=200, screen=None):
    """Run a shell command on the computer. Returns (exit_code, output)."""
    if comp["id"] == "local":
        try:
            p = subprocess.run(["bash", "-c", command], capture_output=True, text=True, timeout=timeout + 10)
            return p.returncode, (p.stdout + p.stderr)
        except subprocess.TimeoutExpired:
            return 124, f"timed out after {timeout}s"
    timeout = max(1, min(int(timeout), 300))  # the API clamps to 1..300
    q = {"screen": screen} if screen else None
    r = call("POST", f"/computers/{comp['id']}/bash", {"command": command, "timeout": timeout}, q, timeout=timeout + 60)
    return r.get("exit_code", 1 if not r.get("success") else 0), (r.get("output") or "") + (("\n" + str(r["error"])) if r.get("error") else "")


# --- computers --------------------------------------------------------------------------------

def cmd_list(a):
    comps = computers()
    if a.json:
        print(scrub(json.dumps(comps, indent=2)))
        return
    rows = [("WORKSPACE", "COMPUTER", "ID", "OS", "STATUS", "CPU", "RAM")]
    for c in sorted(comps, key=lambda c: ((c.get("workspace_name") or ""), c.get("name") or "")):
        rows.append((c.get("workspace_name") or "", c.get("name") or "", c["id"][:8], c.get("os") or "", c.get("status") or "",
                     str(c.get("cpu") or ""), f"{c.get('ram') or '?'}G"))
    w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for r in rows:
        print(scrub("  ".join(v.ljust(x) for v, x in zip(r, w)).rstrip()))


def cmd_get(a):
    c = resolve(a.computer)
    rec = c if c["id"] == "local" else clean(call("GET", f"/computers/{c['id']}"))
    print(scrub(json.dumps(rec, indent=2)))


def cmd_lifecycle(a):
    if not a.yes:
        die(f"{a.cmd} changes the computer. Get the owner's explicit yes, then rerun with --yes.", 4)
    c = resolve(a.computer)
    if c["id"] == "local":
        die("lifecycle commands need a real computer, not local")
    r = call("POST", f"/computers/{c['id']}/{a.cmd}")
    print(scrub(json.dumps(clean(r) if isinstance(r, dict) else r, indent=2)))


# --- actions ------------------------------------------------------------------------------------

def cmd_bash(a):
    c = resolve(a.computer)
    rc, out = bash(c, a.command, a.timeout, a.screen)
    print(scrub(out.rstrip()))
    sys.exit(0 if rc == 0 else (rc if 0 < rc < 256 else 1))


def cmd_exec(a):
    c = resolve(a.computer)
    code = a.code if a.code else open(a.file).read()
    if c["id"] == "local":
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=a.timeout + 10)
        print(scrub((p.stdout + p.stderr).rstrip()))
        sys.exit(p.returncode)
    r = call("POST", f"/computers/{c['id']}/exec", {"code": code, "timeout": max(1, min(a.timeout, 300))}, timeout=a.timeout + 60)
    print(scrub((r.get("output") or "").rstrip()))
    sys.exit(0 if r.get("success") else 1)


def cmd_push(a):
    """Copy a local folder to the computer: tar.gz, sent in base64 chunks over bash, unpacked into <remote-dir>.
    Files already there with the same names are overwritten; nothing else in <remote-dir> is touched."""
    c = resolve(a.computer)
    src = os.path.abspath(a.local_dir.rstrip("/"))
    if not os.path.isdir(src):
        die(f"{src} is not a folder")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(src, arcname=".", filter=lambda ti: None if re.search(r"(^|/)(\.env[^/]*|\.git|__pycache__|\.DS_Store)$", ti.name) else ti)
    data = base64.b64encode(buf.getvalue()).decode()
    dest = a.remote_dir
    if "'" in dest:
        die("remote dir may not contain a single quote")
    tmp = f"/tmp/orgo-push-{os.urandom(4).hex()}.b64"
    size = 200_000
    chunks = [data[i:i + size] for i in range(0, len(data), size)] or [""]
    for n, chunk in enumerate(chunks):
        rc, out = bash(c, f"printf %s '{chunk}' >> {tmp}", 120)
        if rc:
            die(f"push failed at chunk {n + 1}/{len(chunks)}: {out[-300:]}")
    rc, out = bash(c, f"set -e; mkdir -p '{dest}'; (base64 -d < {tmp} 2>/dev/null || base64 -D -i {tmp}) | tar -xzf - -C '{dest}'; rm -f {tmp}; "
                      f"find '{dest}' -type f | wc -l", 180)
    if rc:
        die(f"unpack failed: {out[-300:]}")
    print(json.dumps({"computer": c.get("name"), "dest": dest, "chunks": len(chunks), "bytes": len(buf.getvalue()), "files_in_dest": out.strip().splitlines()[-1] if out.strip() else "?"}))


def act(a, path, body, screen=None):
    c = resolve(a.computer)
    if c["id"] == "local":
        die("GUI actions go through the Orgo API; name the computer instead of local")
    r = call("POST", f"/computers/{c['id']}/{path}", body, {"screen": screen} if screen else None)
    print(scrub(json.dumps(r)))


def cmd_screenshot(a):
    c = resolve(a.computer)
    q = {"response_format": "base64", "format": "png"}
    if a.scale:
        q["scale"] = a.scale
    if a.screen:
        q["screen"] = a.screen
    r = call("GET", f"/computers/{c['id']}/screenshot", query=q)
    img = base64.b64decode(r.get("image") or "")
    out = a.output or f"orgo-{c['id'][:8]}-{int(time.time())}.png"
    with open(out, "wb") as f:
        f.write(img)
    print(json.dumps({"file": os.path.abspath(out), "width": r.get("width"), "height": r.get("height"), "bytes": len(img)}))


# --- Hermes -------------------------------------------------------------------------------------
# An "agent" is one Hermes install on the computer: a container (docker:<name>) or a host user
# (host:<user>). agents() prints label|uid|hermes-bin|HERMES_HOME. Works on Linux and macOS.

LIB = r'''
set +e
T=${T:-120}
OS=$(uname -s)
tmo() { if command -v timeout >/dev/null 2>&1; then timeout -k 10 "$T" "$@"; elif command -v gtimeout >/dev/null 2>&1; then gtimeout -k 10 "$T" "$@"; else perl -e 'alarm shift; exec @ARGV' "$T" "$@"; fi; }
hbin() { command -v hermes 2>/dev/null || for p in "$HOME/.local/bin/hermes" "$HOME/hermes-agent/venv/bin/hermes" "$HOME/hermes-agent/.venv/bin/hermes" /usr/local/bin/hermes /opt/homebrew/bin/hermes; do [ -x "$p" ] && { echo "$p"; break; }; done; }
detect() {
  if [ "$OS" = Darwin ]; then
    b=$(hbin); [ -n "$b" ] && echo "host:$(id -un)|$(id -u)|$b|${HERMES_HOME:-$HOME/.hermes}"
    return
  fi
  if command -v docker >/dev/null 2>&1; then
    for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do
      h=$(docker exec "$c" sh -c 'command -v hermes >/dev/null 2>&1 && printf %s "${HERMES_HOME:-$HOME/.hermes}"' 2>/dev/null </dev/null)
      [ -n "$h" ] || continue
      u=$(docker exec "$c" stat -c %u "$h" 2>/dev/null </dev/null); [ -n "$u" ] || u=0
      echo "docker:$c|$u|hermes|$h"
    done
  fi
  hostns=$(readlink /proc/1/ns/mnt)
  ps -eo pid=,uid=,args= | awk '{b="";g=0;for(i=3;i<=NF;i++){n=$i;sub(/.*\//,"",n);if(b==""&&n=="hermes")b=$i;else if(b!=""&&$i=="gateway")g=1}if(b!=""&&g)print $1,$2,b}' |
  while read -r pid uid bin; do
    [ "$(readlink /proc/$pid/ns/mnt 2>/dev/null)" = "$hostns" ] || continue
    user=$(id -nu "$uid" 2>/dev/null) || continue
    h=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | sed -n 's/^HERMES_HOME=//p' | head -1)
    [ -n "$h" ] || h="$(getent passwd "$user" | cut -d: -f6)/.hermes"
    [ "$uid" = 0 ] && command -v hermes >/dev/null 2>&1 && bin=$(command -v hermes)
    case $bin in /*) ;; *) bin=$(command -v "$bin") ;; esac
    echo "host:$user|$uid|$bin|$h"
  done
  b=$(hbin); [ -n "$b" ] && echo "host:$(id -un)|$(id -u)|$b|${HERMES_HOME:-$HOME/.hermes}"
}
agents() { detect | awk -F'|' 'NF==4 && !seen[$1]++'; }
# hx label uid bin home -- args: run hermes as the owner of that HERMES_HOME, bounded by $T.
hx() {
  local label=$1 uid=$2 bin=$3 home=$4 user uhome; shift 4
  case $label in
    docker:*) docker exec -u "$uid" -e HERMES_HOME="$home" "${label#docker:}" sh -c \
                'if command -v timeout >/dev/null 2>&1; then exec timeout -k 10 "$0" hermes "$@"; else exec hermes "$@"; fi' "$T" "$@" </dev/null ;;
    *) if [ "$uid" = "$(id -u)" ]; then tmo env HERMES_HOME="$home" "$bin" "$@" </dev/null
       else
         user=$(id -nu "$uid"); uhome=$(getent passwd "$user" 2>/dev/null | cut -d: -f6); [ -n "$uhome" ] || uhome=$(eval echo "~$user")
         if command -v runuser >/dev/null 2>&1; then runuser -u "$user" -- timeout -k 10 "$T" env HOME="$uhome" HERMES_HOME="$home" "$bin" "$@" </dev/null
         else sudo -n -u "$user" env HOME="$uhome" HERMES_HOME="$home" "$bin" "$@" </dev/null; fi
       fi ;;
  esac
}
profiles() { hx "$@" profile list 2>/dev/null | awk '/───|Profile[ ]+Model/{next} NF>=3{d=($0 ~ /◆/)?"*":"";gsub("◆","");print $1"|"$2"|"$3"|"d}'; }
pick() {
  all=$(agents); m=""
  if [ -n "$SEL" ]; then
    m=$(printf '%s\n' "$all" | awk -F'|' -v s="$SEL" '$1==s || substr($1,index($1,":")+1)==s')
  else
    n_all=$(printf '%s\n' "$all" | grep -c .)
    if [ "$n_all" = 1 ]; then m="$all"
    else
      while IFS='|' read -r label uid bin home; do
        [ -n "$label" ] || continue
        profiles "$label" "$uid" "$bin" "$home" | grep -q '|running|' && m="$m$label|$uid|$bin|$home
"
      done <<EOF
$all
EOF
    fi
  fi
  n=$(printf '%s' "$m" | grep -c .)
  if [ "$n" != 1 ]; then echo "PICK|$n"; printf '%s\n' "$all" | cut -d'|' -f1 | grep . | sed 's/^/CAND|/'; exit 3; fi
  IFS='|' read -r A_LABEL A_UID A_BIN A_HOME <<EOF
$m
EOF
  echo "USING|$A_LABEL"
  PDIR="$A_HOME"; [ -n "$PROFILE" ] && PDIR="$A_HOME/profiles/$PROFILE"
}
# run a command as the agent's owner (for files inside HERMES_HOME)
asown() {
  case $A_LABEL in
    docker:*) docker exec -i -u "$A_UID" "${A_LABEL#docker:}" sh -c "$1" ;;
    *) if [ "$A_UID" = "$(id -u)" ]; then sh -c "$1"
       elif command -v runuser >/dev/null 2>&1; then runuser -u "$(id -nu "$A_UID")" -- sh -c "$1"
       else sudo -n -u "$(id -nu "$A_UID")" sh -c "$1"; fi ;;
  esac
}
'''

STATUS = r'''
echo "OS|$OS"
if [ "$OS" = Darwin ]; then
  echo "UP|$(( $(date +%s) - $(sysctl -n kern.boottime | sed -E 's/.*[{] sec = ([0-9]+).*/\1/') ))"
  echo "MEM|$(( $(sysctl -n hw.memsize) / 1048576 ))|$(vm_stat | awk '/Pages free|Pages inactive/{gsub(/\./,"",$NF);s+=$NF}END{print int(s*4096/1048576)}')"
  df -g / | awk 'NR==2{print "DISK|"$2"|"$3}'
else
  read -r up _ < /proc/uptime; echo "UP|${up%.*}"
  free -m | awk 'NR==2{print "MEM|"$2"|"$7}'
  df -BG / | awk 'NR==2{gsub("G","",$2);gsub("G","",$3);print "DISK|"$2"|"$3}'
fi
if [ -n "$STOPFILE" ]; then
  if [ -e "$STOPFILE" ]; then echo "STOP|present"
  elif command -v docker >/dev/null 2>&1; then for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do docker exec "$c" test -e "$STOPFILE" 2>/dev/null </dev/null && { echo "STOP|present"; break; }; done; fi
fi
agents | while IFS='|' read -r label uid bin home; do
  [ -n "$SEL" ] && [ "$label" != "$SEL" ] && [ "${label#*:}" != "$SEL" ] && continue
  v=$(hx "$label" "$uid" "$bin" "$home" --version 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  echo "AGENT|$label|${v:-?}"
  profiles "$label" "$uid" "$bin" "$home" | awk -v L="$label" '{print "PROF|" L "|" $0}'
done
'''

ASK = r'''
pick
MSG=$(printf %s "$B64" | base64 -d 2>/dev/null || printf %s "$B64" | base64 -D)
set -- chat -q "$MSG" -Q --source tool --max-turns "$MT"
[ -n "$RESUME" ] && set -- "$@" --resume "$RESUME"
[ -n "$PROFILE" ] && set -- -p "$PROFILE" "$@"
echo "REPLY|"
hx "$A_LABEL" "$A_UID" "$A_BIN" "$A_HOME" "$@" 2>&1
echo "EXIT|$?"
'''

# Long tasks: detached under a job folder the agent's owner can write. The founder collects with result.
START = r'''
pick
J="$A_HOME/.orgo-jobs/$JOB"
asown "mkdir -p '$J'"
printf %s "$B64" | (base64 -d 2>/dev/null || base64 -D) | asown "cat > '$J/task.md'"
printf %s "$RUNNER" | (base64 -d 2>/dev/null || base64 -D) | asown "cat > '$J/run.sh'"
printf "HBIN='%s'\nPROFILE='%s'\nMT='%s'\nJT='%s'\nHERMES_HOME='%s'\nexport HERMES_HOME\n" "$A_BIN" "$PROFILE" "$MT" "$JT" "$A_HOME" | asown "cat > '$J/job.env'"
case $A_LABEL in
  docker:*) docker exec -d -u "$A_UID" -e HERMES_HOME="$A_HOME" "${A_LABEL#docker:}" sh "$J/run.sh" ;;
  *) asown "nohup sh '$J/run.sh' </dev/null >/dev/null 2>&1 &" ;;
esac
echo "JOB|$JOB"
'''

RUNNER = r'''#!/bin/sh
cd "$(dirname "$0")" || exit 1
. ./job.env
date +%s > started
set -- chat -q "$(cat task.md)" -Q --source tool --max-turns "$MT"
[ -n "$PROFILE" ] && set -- -p "$PROFILE" "$@"
if command -v timeout >/dev/null 2>&1; then timeout -k 10 "$JT" "$HBIN" "$@" >out.txt 2>&1 </dev/null
elif command -v gtimeout >/dev/null 2>&1; then gtimeout -k 10 "$JT" "$HBIN" "$@" >out.txt 2>&1 </dev/null
else perl -e 'alarm shift; exec @ARGV' "$JT" "$HBIN" "$@" >out.txt 2>&1 </dev/null; fi
echo $? > exit
'''

RESULT = r'''
pick
J="$A_HOME/.orgo-jobs/$JOB"
if ! asown "test -d '$J'"; then echo "NOTE|no such job $JOB"; exit 5; fi
if asown "test -f '$J/exit'"; then echo "STATE|done"; echo "EXITCODE|$(asown "cat '$J/exit'")"; else echo "STATE|running"; fi
asown "tail -c 60000 '$J/out.txt' 2>/dev/null"
'''

LOGS = r'''
pick
f="$PDIR/logs/$WHICH.log"
echo "FILE|$f"
if asown "test -f '$f'"; then asown "tail -n $N '$f'"; else echo "NOTE|$f not found; log files there:"; asown "ls '$PDIR/logs'" 2>/dev/null; fi
'''

CRON = r'''
pick
set -- cron list
[ -n "$PROFILE" ] && set -- -p "$PROFILE" "$@"
hx "$A_LABEL" "$A_UID" "$A_BIN" "$A_HOME" "$@" 2>&1
'''

SKILL_INSTALL = r'''
pick
S="$PDIR/skills"; TS=$(date +%Y%m%d-%H%M%S)
asown "mkdir -p '$S/.backup'"
if asown "test -d '$S/$NAME'"; then asown "mv '$S/$NAME' '$S/.backup/$NAME-$TS'" && echo "BACKUP|$S/.backup/$NAME-$TS"; fi
printf %s "$B64" | (base64 -d 2>/dev/null || base64 -D) | asown "tar -xzf - -C '$S'"
asown "test -f '$S/$NAME/SKILL.md'" && echo "INSTALLED|$S/$NAME" || { echo "NOTE|install failed"; exit 6; }
'''

SKILL_ROLLBACK = r'''
pick
S="$PDIR/skills"
last=$(asown "ls -1d '$S/.backup/$NAME-'* 2>/dev/null | sort | tail -1")
if asown "test -d '$S/$NAME'"; then asown "mv '$S/$NAME' '$S/.backup/$NAME-removed-$(date +%Y%m%d-%H%M%S)'"; fi
if [ -n "$last" ]; then asown "mv '$last' '$S/$NAME'" && echo "RESTORED|$last"; else echo "REMOVED|$NAME (no earlier version)"; fi
'''


def script(body, **env):
    return "".join(f"{k}={shlex.quote(str(v))}\n" for k, v in env.items()) + LIB + body


def safe_name(v, what):
    if v and not re.fullmatch(r"[A-Za-z0-9._:-]+", v):
        die(f"bad {what}: {v!r}")
    return v or ""


def markers(out):
    meta, body = {}, []
    for line in out.splitlines():
        p = line.split("|", 1)
        if p[0] in ("USING", "PICK", "EXIT", "FILE", "JOB", "STATE", "EXITCODE", "BACKUP", "INSTALLED", "RESTORED", "REMOVED", "OS", "STOP") and len(p) == 2:
            meta[p[0]] = p[1]
        elif p[0] == "CAND" and len(p) == 2:
            meta.setdefault("CAND", []).append(p[1])
        elif p[0] == "REPLY":
            continue
        elif p[0] == "NOTE" and len(p) == 2:
            body.append("note: " + p[1])
        else:
            body.append(line)
    return meta, "\n".join(body).strip()


def run_box(a, body, timeout=120, **env):
    c = resolve(a.computer)
    env.setdefault("SEL", safe_name(getattr(a, "agent", None), "agent"))
    env.setdefault("PROFILE", safe_name(getattr(a, "profile", None), "profile"))
    env.setdefault("T", timeout)
    rc, out = bash(c, script(body, **env), timeout + 20)
    meta, text = markers(out)
    if "PICK" in meta:
        why = "no Hermes agent with a running gateway" if meta["PICK"] == "0" else "more than one Hermes agent"
        die(f"{c['name']}: {why}. Pass --agent with one of: {', '.join(meta.get('CAND', [])) or '(none found)'}", 3)
    return c, rc, meta, text


def h_agents(a):
    c = resolve(a.computer)
    rc, out = bash(c, script(STATUS, T=60, SEL=safe_name(getattr(a, "agent", None), "agent")), 150)
    cmd_status_print(c, out, as_json=getattr(a, "json", False))


def cmd_status(a):
    c = resolve(a.computer)
    rc, out = bash(c, script(STATUS, T=60, STOPFILE=a.stop_file or "", SEL=safe_name(a.agent, "agent")), 150)
    cmd_status_print(c, out, as_json=a.json)


def cmd_status_print(c, out, as_json=False):
    row = {"computer": c.get("name"), "id": c["id"], "os": None, "agents": {}, "stop": False}
    for line in out.splitlines():
        p = line.split("|")
        if p[0] == "OS" and len(p) > 1:
            row["os"] = p[1]
        elif p[0] == "UP" and len(p) > 1 and p[1].lstrip("-").isdigit():
            row["uptime_h"] = round(int(p[1]) / 3600, 1)
        elif p[0] == "MEM" and len(p) > 2 and p[1].isdigit() and p[2].isdigit():
            row["mem_total_mb"], row["mem_avail_mb"] = int(p[1]), int(p[2])
        elif p[0] == "DISK" and len(p) > 2:
            row["disk_gb"], row["disk_used_gb"] = p[1], p[2]
        elif p[0] == "STOP":
            row["stop"] = True
        elif p[0] == "AGENT" and len(p) > 2:
            row["agents"][p[1]] = {"version": p[2], "profiles": []}
        elif p[0] == "PROF" and len(p) > 5 and p[1] in row["agents"]:
            row["agents"][p[1]]["profiles"].append({"name": p[2], "model": p[3], "gateway": p[4], "default": p[5] == "*"})
    if "mem_total_mb" not in row:
        row["error"] = scrub(out.strip().splitlines()[-1] if out.strip() else "no answer")
    if as_json:
        print(scrub(json.dumps(row, indent=2)))
        return
    if row.get("error"):
        die(f"{row['computer']}: {row['error']}", 2)
    used = (row["mem_total_mb"] - row["mem_avail_mb"]) / max(row["mem_total_mb"], 1)
    print(f"{row['computer']}  os={row['os']}  up={row.get('uptime_h')}h  ram={used:.0%} of {row['mem_total_mb'] // 1024}G  disk={row.get('disk_used_gb')}/{row.get('disk_gb')}G" + ("  STOP FILE PRESENT" if row["stop"] else ""))
    if not row["agents"]:
        print("  no Hermes agent found")
    for label, ag in row["agents"].items():
        on = [p["name"] + ("*" if p["default"] else "") for p in ag["profiles"] if p["gateway"] == "running"]
        off = [p["name"] for p in ag["profiles"] if p["gateway"] != "running"]
        print(scrub(f"  {label} {ag['version']}: {len(ag['profiles'])} profiles; gateway running: {', '.join(on) or 'none'}" + (f"; stopped: {len(off)}" if off else "")))


def h_ask(a):
    t = max(10, min(a.timeout, 280))
    b64 = base64.b64encode(a.message.encode()).decode()
    c, rc, meta, text = run_box(a, ASK, t, B64=b64, MT=a.max_turns, RESUME=safe_name(a.resume, "session id"))
    print(f"-> {c['name']} / {meta.get('USING', '?')}" + (f" / {a.profile}" if a.profile else ""), file=sys.stderr)
    print(scrub(text))
    code = meta.get("EXIT", str(rc))
    if code != "0":
        die(f"hermes exited {code}" + (" (timed out: use `hermes start` for long tasks)" if code in ("124", "137", "142") else ""), 1)


def h_start(a):
    msg = a.message if a.message else open(a.file).read()
    job = time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex()
    b64 = base64.b64encode(msg.encode()).decode()
    runner = base64.b64encode(RUNNER.encode()).decode()
    c, rc, meta, text = run_box(a, START, 60, B64=b64, JOB=job, MT=int(a.max_turns), JT=int(a.job_timeout), RUNNER=runner)
    if meta.get("JOB") != job:
        die(f"could not start the job: {text[-400:]}")
    print(json.dumps({"computer": c["name"], "agent": meta.get("USING"), "profile": a.profile, "job": job}))


def h_result(a):
    c, rc, meta, text = run_box(a, RESULT, 60, JOB=safe_name(a.job, "job id"))
    print(json.dumps({"job": a.job, "state": meta.get("STATE", "unknown"), "exit": meta.get("EXITCODE")}), file=sys.stderr)
    print(scrub(text))


def h_logs(a):
    if a.file not in ("gateway", "errors", "agent"):
        die("--file must be gateway, errors or agent")
    c, rc, meta, text = run_box(a, LOGS, 60, N=int(a.n), WHICH=a.file)
    print(f"-> {c['name']} / {meta.get('USING', '?')} / {meta.get('FILE', '?')}", file=sys.stderr)
    print(scrub(text))


def h_cron(a):
    c, rc, meta, text = run_box(a, CRON, 60)
    print(scrub(text))


def h_skill_install(a):
    if not a.yes:
        die("skill-install writes into a live agent. Rerun with --yes once you hold the authority for it.", 4)
    src = os.path.abspath(a.skill_dir.rstrip("/"))
    name = os.path.basename(src)
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        die(f"{src} has no SKILL.md")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(src, arcname=name, filter=lambda ti: None if re.search(r"(^|/)(\.env|\.git|__pycache__)", ti.name) else ti)
    if buf.tell() > 3_000_000:
        die("skill folder is over 3 MB packed; slim it or upload it with the files API")
    b64 = base64.b64encode(buf.getvalue()).decode()
    c, rc, meta, text = run_box(a, SKILL_INSTALL, 120, B64=b64, NAME=safe_name(name, "skill name"))
    print(json.dumps({k.lower(): v for k, v in meta.items() if k in ("USING", "BACKUP", "INSTALLED")}))
    if "INSTALLED" not in meta:
        die(text or "install failed")


def h_skill_rollback(a):
    if not a.yes:
        die("skill-rollback writes into a live agent. Rerun with --yes once you hold the authority for it.", 4)
    c, rc, meta, text = run_box(a, SKILL_ROLLBACK, 60, NAME=safe_name(a.name, "skill name"))
    print(json.dumps({k.lower(): v for k, v in meta.items() if k in ("USING", "RESTORED", "REMOVED")}))


# --- CLI ---------------------------------------------------------------------------------------

def main():
    global KEY
    ap = argparse.ArgumentParser(description="Connect to, run and control Orgo cloud computers and their Hermes agents.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_list)
    s = sub.add_parser("get"); s.add_argument("computer"); s.set_defaults(fn=cmd_get)
    s = sub.add_parser("status"); s.add_argument("computer"); s.add_argument("--json", action="store_true")
    s.add_argument("--stop-file", help="path of the box's STOP file, reported if present")
    s.add_argument("--agent", help="probe only this Hermes install (docker:<name> or host:<user>)"); s.set_defaults(fn=cmd_status)
    for name in ("start", "stop", "restart"):
        s = sub.add_parser(name); s.add_argument("computer"); s.add_argument("--yes", action="store_true"); s.set_defaults(fn=cmd_lifecycle)

    s = sub.add_parser("bash"); s.add_argument("computer"); s.add_argument("command")
    s.add_argument("--timeout", type=int, default=120); s.add_argument("--screen"); s.set_defaults(fn=cmd_bash)
    s = sub.add_parser("exec"); s.add_argument("computer"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--code"); g.add_argument("--file"); s.add_argument("--timeout", type=int, default=60); s.set_defaults(fn=cmd_exec)
    s = sub.add_parser("push", help="copy a local folder onto the computer"); s.add_argument("computer"); s.add_argument("local_dir")
    s.add_argument("remote_dir"); s.set_defaults(fn=cmd_push)
    s = sub.add_parser("screenshot"); s.add_argument("computer"); s.add_argument("-o", "--output")
    s.add_argument("--scale", type=float); s.add_argument("--screen"); s.set_defaults(fn=cmd_screenshot)
    s = sub.add_parser("click"); s.add_argument("computer"); s.add_argument("x", type=int); s.add_argument("y", type=int)
    s.add_argument("--right", action="store_true"); s.add_argument("--double", action="store_true"); s.add_argument("--screen")
    s.set_defaults(fn=lambda a: act(a, "click", {"x": a.x, "y": a.y, "button": "right" if a.right else "left", "double": a.double}, a.screen))
    s = sub.add_parser("type"); s.add_argument("computer"); s.add_argument("text"); s.add_argument("--screen")
    s.set_defaults(fn=lambda a: act(a, "type", {"text": a.text}, a.screen))
    s = sub.add_parser("key"); s.add_argument("computer"); s.add_argument("key"); s.add_argument("--screen")
    s.set_defaults(fn=lambda a: act(a, "key", {"key": a.key}, a.screen))
    s = sub.add_parser("scroll"); s.add_argument("computer"); s.add_argument("x", type=int); s.add_argument("y", type=int)
    s.add_argument("--up", action="store_true"); s.add_argument("--amount", type=int, default=3); s.add_argument("--screen")
    s.set_defaults(fn=lambda a: act(a, "scroll", {"x": a.x, "y": a.y, "direction": "up" if a.up else "down", "amount": a.amount}, a.screen))
    s = sub.add_parser("drag"); s.add_argument("computer")
    for k in ("x1", "y1", "x2", "y2"):
        s.add_argument(k, type=int)
    s.add_argument("--screen")
    s.set_defaults(fn=lambda a: act(a, "drag", {"start_x": a.x1, "start_y": a.y1, "end_x": a.x2, "end_y": a.y2}, a.screen))
    s = sub.add_parser("wait"); s.add_argument("computer"); s.add_argument("seconds", type=float)
    s.set_defaults(fn=lambda a: act(a, "wait", {"seconds": a.seconds}))

    h = sub.add_parser("hermes", help="drive the Hermes agents on a computer").add_subparsers(dest="hcmd", required=True)

    def common(p):
        p.add_argument("computer"); p.add_argument("--agent", help="docker:<name> or host:<user> when the computer has several Hermes installs")
        p.add_argument("--profile", help="Hermes profile (default: the agent's sticky default)")
        return p
    s = h.add_parser("agents"); s.add_argument("computer"); s.add_argument("--json", action="store_true"); s.add_argument("--agent"); s.set_defaults(fn=h_agents)
    s = common(h.add_parser("ask")); s.add_argument("message"); s.add_argument("--resume"); s.add_argument("--max-turns", type=int, default=20)
    s.add_argument("--timeout", type=int, default=240, help="seconds, at most 280 (one API call); longer work: hermes start"); s.set_defaults(fn=h_ask)
    s = common(h.add_parser("start")); g = s.add_mutually_exclusive_group(required=True); g.add_argument("--message"); g.add_argument("--file")
    s.add_argument("--max-turns", type=int, default=60); s.add_argument("--job-timeout", type=int, default=3600); s.set_defaults(fn=h_start)
    s = common(h.add_parser("result")); s.add_argument("job"); s.set_defaults(fn=h_result)
    s = common(h.add_parser("logs")); s.add_argument("n", nargs="?", default=50); s.add_argument("--file", default="gateway"); s.set_defaults(fn=h_logs)
    s = common(h.add_parser("cron")); s.set_defaults(fn=h_cron)
    s = common(h.add_parser("skill-install")); s.add_argument("skill_dir"); s.add_argument("--yes", action="store_true"); s.set_defaults(fn=h_skill_install)
    s = common(h.add_parser("skill-rollback")); s.add_argument("name"); s.add_argument("--yes", action="store_true"); s.set_defaults(fn=h_skill_rollback)

    a = ap.parse_args()
    target = getattr(a, "computer", None)
    KEY = load_key(required=target != "local")
    a.fn(a)


if __name__ == "__main__":
    main()
