#!/usr/bin/env python3
"""HeyGen, for the content job: turn a finished script into an avatar video. Standard library only.

    heygen.py check                         remaining credit: proves the key reads
    heygen.py avatars | voices              what the account has, with ids
    heygen.py render --script-file F [--avatar ID] [--voice ID] [--portrait|--landscape] [--title T]
    heygen.py status <video_id>             the state, and the video's URL when it is done
    heygen.py fetch <video_id> --out F.mp4  save a finished video into the workspace

Needs HEYGEN_API_KEY, from the environment or a KEY=value line in <workspace>/.secrets/*.env. The default avatar and
voice are HEYGEN_AVATAR_ID and HEYGEN_VOICE_ID in the same file, or the two lines in context/heygen.md.

A render spends HeyGen credit, so it asks the spend guard first: context/spend-approvals.md needs the line
`heygen: approved <N>`, where N is the most videos a day. Without it, or past N, or with no key, nothing is rendered:
the exact command is added to requests/justin/video-renders-<date>.md and RENDER HELD is printed. The script is still
finished and waiting, so the day's content is never blocked by a render.

Written from HeyGen's public API pages (v2 video generate, v1 video status). Not run against an account."""
import argparse, datetime, json, os, pathlib, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
WS = pathlib.Path(os.environ.get("BOT_HOME") or (REPO.parent if REPO.name == "repo" else REPO))
API = "https://api.heygen.com"
TODAY = f"{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d}"


def setting(name):
    if os.environ.get(name):
        return os.environ[name]
    sec = WS / ".secrets"
    for f in sorted(sec.glob("*.env")) if sec.is_dir() else []:
        for l in f.read_text(errors="ignore").splitlines():
            k, _, v = l.strip().partition("=")
            if k == name and v:
                return v.strip().strip('"')
    f = WS / "context" / "heygen.md"
    for l in f.read_text(errors="ignore").splitlines() if f.exists() else []:
        k, _, v = l.strip().partition(":")
        if k.strip().upper() == name and v.strip():
            return v.strip()
    return ""


def call(method, path, body=None, query=None):
    key = setting("HEYGEN_API_KEY")
    if not key:
        sys.exit("Set HEYGEN_API_KEY (hidden prompt; it goes in the workspace's .secrets/ file).")
    url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"X-Api-Key": key, "Accept": "application/json", "Content-Type": "application/json", "User-Agent": "find-me-money-bot/1"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}")
    except urllib.error.URLError as e:
        sys.exit(f"{method} {path} -> no answer: {e.reason}")


def rendered_today():
    f = WS / "log" / "heygen.jsonl"
    return sum(1 for l in f.read_text().splitlines() if l.startswith('{"date": "' + TODAY)) if f.exists() else 0


def held(why):
    d = WS / "requests" / "justin"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"video-renders-{TODAY}.md"
    if not f.exists():
        f.write_text("# Videos the bot would have rendered in HeyGen\n\nNot rendered: a render spends credit. Each line is the exact command.\n\n")
    with f.open("a") as h:
        h.write("- `python3 repo/tools/heygen.py " + " ".join(a if re.fullmatch(r"[\w@.:/,+-]+", a) else json.dumps(a) for a in sys.argv[1:]) + f"`  ({why})\n")
    print(f"RENDER HELD ({why}): {f}")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd"); ap.add_argument("args", nargs="*")
    for f in ("script-file", "avatar", "voice", "title", "out"):
        ap.add_argument("--" + f)
    ap.add_argument("--portrait", action="store_true"); ap.add_argument("--landscape", action="store_true")
    a = ap.parse_args(); c, x = a.cmd, a.args
    if c == "check":
        print(json.dumps(call("GET", "/v2/user/remaining_quota").get("data", {})))
    elif c in ("avatars", "voices"):
        d = call("GET", f"/v2/{c}").get("data", {})
        for it in d.get(c, [])[:200]:
            print(it.get("avatar_id") or it.get("voice_id"), "|", it.get("avatar_name") or it.get("name"), "|", it.get("gender", ""), it.get("language", ""))
    elif c == "render":
        text = pathlib.Path(a.script_file).read_text().strip()
        if not text:
            sys.exit("the script file is empty")
        if len(text) > 4900:
            sys.exit("the script is over 4,900 characters: HeyGen takes less per scene. Cut it or split it.")
        n = rendered_today() + 1
        r = subprocess.run([sys.executable, str(REPO / "guards" / "scripts" / "spend_guard.py"), "heygen", str(n)], capture_output=True, text=True, env=dict(os.environ, BOT_HOME=str(WS)))
        if r.returncode != 0:
            held(f"no line `heygen: approved <videos a day>` covers video {n} today")
        if not setting("HEYGEN_API_KEY"):
            held("the HeyGen key is not set")
        avatar, voice = a.avatar or setting("HEYGEN_AVATAR_ID"), a.voice or setting("HEYGEN_VOICE_ID")
        if not (avatar and voice):
            held("no avatar or voice chosen yet (HEYGEN_AVATAR_ID, HEYGEN_VOICE_ID)")
        w, h = (1280, 720) if a.landscape else (720, 1280)
        out = call("POST", "/v2/video/generate", {"title": a.title or pathlib.Path(a.script_file).stem, "dimension": {"width": w, "height": h},
                   "video_inputs": [{"character": {"type": "avatar", "avatar_id": avatar, "avatar_style": "normal"}, "voice": {"type": "text", "input_text": text, "voice_id": voice}}]})
        vid = (out.get("data") or {}).get("video_id", "?")
        (WS / "log").mkdir(exist_ok=True)
        with (WS / "log" / "heygen.jsonl").open("a") as f:
            f.write(json.dumps({"date": TODAY, "video_id": vid, "script": a.script_file}) + "\n")
        print(f"rendering: {vid}")
    elif c == "status":
        d = call("GET", "/v1/video_status.get", query={"video_id": x[0]}).get("data", {})
        print(d.get("status", "?"), d.get("video_url") or "")
    elif c == "fetch":
        d = call("GET", "/v1/video_status.get", query={"video_id": x[0]}).get("data", {})
        if d.get("status") != "completed" or not d.get("video_url"):
            sys.exit(f"not done yet: {d.get('status', '?')}")
        out = (WS / a.out).resolve() if not os.path.isabs(a.out) else pathlib.Path(a.out).resolve()
        if WS.resolve() not in out.parents:
            sys.exit("--out must be inside the workspace")
        out.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(d["video_url"], out)
        print("saved", out)
    else:
        sys.exit("Unknown command. Run with -h.")


if __name__ == "__main__":
    main()
