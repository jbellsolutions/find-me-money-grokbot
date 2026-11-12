"""Shared: find the workspace. The pack lives at <workspace>/repo/, so the workspace is three levels up
from repo/guards/scripts/. BOT_HOME overrides it (tests use a scratch folder)."""
import os, pathlib
WS = pathlib.Path(os.environ.get("BOT_HOME") or pathlib.Path(__file__).resolve().parents[3])
def p(*parts): return WS.joinpath(*parts)
def stopped(): return p("context", "STOP").exists()
def norm(s): return " ".join("".join(c.lower() if c.isalnum() or c in "@." else " " for c in s).split())


def never_touch():
    """The private never-touch list: computers, agents, accounts and organizations the bot must never use, not even
    to read. From env NEVER_TOUCH (comma-separated), else <workspace>/.secrets/never-touch.txt (one per line, # comments).
    The names are Justin's and never ship in the pack. Returns a set of lower-cased names, or None when there is no
    list (missing or empty): then every guarded write is refused (fail closed)."""
    raw = os.environ.get("NEVER_TOUCH", "")
    names = [x for x in raw.split(",")]
    if not raw.strip():
        f = p(".secrets", "never-touch.txt")
        try:
            names = [l.split("#", 1)[0] for l in f.read_text(errors="ignore").splitlines()]
        except OSError:
            names = []
    out = {n.strip().lower() for n in names if n.strip()}
    return out or None


def touch_refusal(*targets):
    """None if every target may be used; otherwise the reason it's refused."""
    nt = never_touch()
    if nt is None:
        return "refused: no never-touch list (set NEVER_TOUCH or .secrets/never-touch.txt at intake)"
    for t in targets:
        t = (t or "").strip().lower()
        if t and any(n == t or n in t for n in nt):
            return "refused: target is on the never-touch list"
    return None
