"""Settings for the Reply Agent. Every value can come from the environment or `$REPLY_HOME/reply.env`.

Nothing secret lives in this repo. The Lead Radar password and the Anthropic key sit in the Hermes profile's `.env`
(passed to the MCP server through `${env:...}` references) or in `reply.env` on the agent's own computer.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env(name: str, default: str = "") -> str:
    """An env value, treating Hermes' unresolved `${env:NAME}` placeholder (a key the profile's .env lacks) as unset."""
    value = os.environ.get(name, "")
    return default if not value or value.startswith("${") else value


def _path(name: str, default: Path | str) -> Path:
    return Path(_env(name) or str(default)).expanduser()


REPLY_HOME = _path("REPLY_HOME", Path.home() / ".pinnacle-reply")
_load_env_file(REPLY_HOME / "reply.env")

STATE_DIR = _path("REPLY_STATE", REPLY_HOME / "state")
LEDGER_DB = STATE_DIR / "ledger.sqlite"
LANES_FILE = _path("REPLY_LANES", REPO_DIR / "config" / "reply-lanes.json")
# Memory is Obsidian: every lead and its whole conversation, as notes in this vault (vault.py), plus the daily ledger.
# On by default in $REPLY_HOME/vault; REPLY_VAULT=off turns it off. It is a git repository: see vault.publish().
VAULT_DIR = None if _env("REPLY_VAULT").strip().lower() in {"off", "0", "false", "no"} \
    else _path("REPLY_VAULT", REPLY_HOME / "vault")
# The vault's name in Justin's Obsidian, for the obsidian:// link on each GHL contact card
VAULT_NAME = _env("REPLY_VAULT_NAME", "Pinnacle Reply Agent")

# Lead Radar (funding-web): the reply queue and the reply desk. Same password as its dashboard.
RADAR_URL = _env("RADAR_URL", "").rstrip("/")
RADAR_PASSWORD = _env("RADAR_PASSWORD", "")

# Writing drafts, holds and marks back to Lead Radar changes a live database, so it stays off until Justin turns it
# on. Off, every cycle still drafts, checks and counts, and keeps its results in the local ledger.
WRITE = _env("REPLY_WRITE", "off").strip().lower() in {"on", "1", "true", "yes"}
WRITER = "reply-agent"  # the `by` it records on Lead Radar; machine drafts carry "draft" or this

# GoHighLevel (ghl.py): each answered lead and its conversation in the CRM. REPLY_GHL_TARGET picks the sub-account:
# funding-machine (the default since D1, 2026-10-25: the Funding Machine is the CRM) or pinnacle-funding-group.
# The writes are always worked out (the outbox); they're sent only with REPLY_GHL on, which is Justin's yes.
GHL = _env("REPLY_GHL", "off").strip().lower() in {"on", "1", "true", "yes"}
GHL_TARGET = _env("REPLY_GHL_TARGET", "pinnacle-funding-group").strip().lower()
GHL_TOKEN = _env("GHL_API_KEY", "")  # Pinnacle Funding Group's private integration token, never the agency's
GHL_LOCATION = _env("GHL_LOCATION_ID", "")
# seen (Justin 2026-11-03: "every lead from Lead Radar should be in Go High Level"): every lead, every tier, as soon as
# the agent reads it; waiting: once it has a checked draft; replied: once a reply is posted
GHL_FROM = _env("REPLY_GHL_FROM", "seen").strip().lower()
GHL_SKIPPED = _env("REPLY_GHL_SKIPPED", "off").strip().lower() in {"on", "1", "true", "yes"}  # skipped leads go in too
# The "Reply Agent · Contact card" note. On until the Funding CRM Manager owns the one card per person (spec 36 section 2);
# REPLY_GHL_CARD=off stops it writing the card. The per-message notes stay.
GHL_CARD = _env("REPLY_GHL_CARD", "on").strip().lower() not in {"off", "0", "false", "no"}
GHL_RECORD = _env("REPLY_GHL_RECORD", "note").strip()  # note, or field:<custom field id>
GHL_MAX = int(_env("REPLY_GHL_MAX", "150"))  # leads sent per cycle: about 1.2 s each, so a cycle stays inside its tool time
GHL_ATTACH_MAX = int(_env("REPLY_GHL_ATTACH_MAX", "100"))  # creators-sync contacts looked up per cycle, one search each
# Facebook leads (MetaMuse answers them, Justin works them, 2026-10-30) get their own pipeline in the Funding Machine and
# go in as soon as they have a checked draft. "off" treats them like every other lead.
GHL_PLATFORM_PIPELINES = _env("REPLY_GHL_PLATFORM_PIPELINES", "on").strip().lower() in {"on", "1", "true", "yes"}

# The other lanes (sources.py). Each is read only when its setting is there; a lane without one is reported as
# not read, with the setting it needs. REPLY_SOURCES picks which lanes to read (default: every one).
# Lead Radar's desk read. With paging (radar-v2-ingest) the agent walks every page of leads posted in the last
# REPLY_DESK_SINCE_DAYS days (0 = all), up to REPLY_DESK_PAGES pages of 1,000. A desk without paging gives one page.
DESK_SINCE_DAYS = int(_env("REPLY_DESK_SINCE_DAYS", "30"))
DESK_PAGES = int(_env("REPLY_DESK_PAGES", "50"))
LANES_ON = {x.strip() for x in _env("REPLY_SOURCES", "").split(",") if x.strip()}
# Creators, startup, direct sales and gig askers: radar-db (schema radar), read in a read-only session. The creators
# lane is the only writer of its ic_* tables, so the agent never writes there. Best given a read-only role's URL.
CREATORS_DB_URL = _env("CREATORS_DB_URL", "")
# Website and app leads: the hosted Lending Hub's deals. The same hub takes the daily check-offs (hub.py).
HUB_URL = _env("HUB_URL", "").rstrip("/")
HUB_PASSWORD = _env("HUB_PASSWORD", "")
# Check-offs and the booked count go to the hub only with REPLY_HUB on. Off, every cycle still works them out.
HUB = _env("REPLY_HUB", "off").strip().lower() in {"on", "1", "true", "yes"}
# The Funding Machine sub-account's inbox and booking calendar, read only. Its token never writes from here.
# FM_GHL_API_KEY, else GHL_API_KEY in FM_GHL_ENV (the file the Funding Machine kit keeps on Justin's Mac).
FM_ENV_FILE = _path("FM_GHL_ENV", Path.home() / ".config" / "funding-machine" / "ghl.env")
FM_GHL_TOKEN = _env("FM_GHL_API_KEY", "")
# Both set at intake (no default ships in the pack). Without FM_GHL_LOCATION_ID the funding-machine target refuses.
FM_GHL_LOCATION = _env("FM_GHL_LOCATION_ID", "")
FM_CALENDARS = [x.strip() for x in _env("FM_GHL_CALENDARS", "").split(",") if x.strip()]
# The home CRM (Pinnacle Funding Group): the pinnacle-funding-group target's pinned location, set at intake. The client
# also checks GHL_LOCATION_ID against it, so a wrong GHL_LOCATION_ID is refused. Unset: that target refuses.
PINNACLE_GHL_LOCATION = _env("PINNACLE_GHL_LOCATION_ID", "")
# Sub-account names this agent never writes to, whatever the location id says (comma-separated, set at intake), plus
# every name on the never-touch list.
NEVER_LOCATIONS = {x.strip().lower() for x in (_env("REPLY_NEVER_LOCATIONS", "") + "," + _env("NEVER_TOUCH", "")).split(",")
                   if x.strip()}

# Claude writes the drafts. Low effort: each one is three or four sentences.
MODEL = _env("REPLY_MODEL", "claude-opus-5-5")
EFFORT = _env("REPLY_EFFORT", "low")
MAX_DRAFTS = int(_env("REPLY_MAX_DRAFTS", "20"))  # per cycle, so one run stays inside the tool timeout
WORKERS = int(_env("REPLY_WORKERS", "4"))  # drafts written side by side in one cycle

# The auto-poster (poster.py): checked drafts posted as replies in the lead's own thread, from the lane's account.
# Off until Justin turns it on. REPLY_POST is the kill switch; REPLY_POST_PLATFORMS names the platforms it may post on.
POST = _env("REPLY_POST", "off").strip().lower() in {"on", "1", "true", "yes"}
POST_PLATFORMS = {x.strip().lower() for x in _env("REPLY_POST_PLATFORMS", "").split(",") if x.strip()}
# Replies per platform per day (Eastern), starting low while the accounts are new; REPLY_POST_CAP_<PLATFORM> overrides
POST_CAP = int(_env("REPLY_POST_CAP", "5"))
POST_CAPS = {k.removeprefix("REPLY_POST_CAP_").lower(): int(v) for k, v in os.environ.items()
             if k.startswith("REPLY_POST_CAP_") and v.strip().isdigit()}
# First replies only to posts this recent; 0 means no limit (Justin's rule to set). Follow-ups follow the conversation.
POST_MAX_AGE_DAYS = float(_env("REPLY_POST_MAX_AGE_DAYS", "3"))
# Following the person who asked, on the platforms that allow it through their API. Its own switch.
FOLLOW = _env("REPLY_FOLLOW", "off").strip().lower() in {"on", "1", "true", "yes"}
# A line added to the end of every automatic post. Justin's decision (charter, 2026-10-31): no bot line on posts, so
# the default is empty and posts go out as drafted; REPLY_POST_BOT_LINE sets one again. Asked directly whether it's
# AI, a reply still answers honestly (charter section 5): that's the drafter's rule, not this line.
POST_BOT_LINE = _env("REPLY_POST_BOT_LINE", "").strip()
# The accounts. Reddit: an app's id and secret plus the refresh token scripts/reddit_token.py gets when the account's
# owner signs in. YouTube: a Google OAuth client plus the refresh token from scripts/youtube_token.py.
REDDIT_CLIENT_ID = _env("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = _env("REDDIT_CLIENT_SECRET", "")
REDDIT_REFRESH_TOKEN = _env("REDDIT_REFRESH_TOKEN", "")
REDDIT_USERNAME = _env("REDDIT_USERNAME", "")
YOUTUBE_CLIENT_ID = _env("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = _env("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = _env("YOUTUBE_REFRESH_TOKEN", "")

# Facebook (platforms/facebook.py): a Chrome window on Justin's Mac with its own profile folder, signed in as his own
# account by him. Only the Mac's browser lane (mac_lane.py) sets REPLY_FACEBOOK_BROWSER; everywhere else Facebook
# shows as posted from the Mac.
FACEBOOK_BROWSER = _env("REPLY_FACEBOOK_BROWSER", "off").strip().lower() in {"on", "1", "true", "yes"}
FACEBOOK_PORT = int(_env("REPLY_FACEBOOK_PORT", "9333"))
FACEBOOK_PROFILE_DIR = _path("REPLY_FACEBOOK_PROFILE",
                             Path.home() / "Library" / "Application Support" / "Pinnacle Reply" / "chrome-facebook")
FACEBOOK_ACCOUNT = _env("REPLY_FACEBOOK_ACCOUNT", "")  # how the posts are labelled, e.g. "Justin Bell (Facebook)"
# The browser lane's pace: posts per run (a run every hour) and the Eastern hours it posts in
POST_PER_RUN = int(_env("REPLY_POST_PER_RUN", "1"))
POST_HOURS = tuple(int(x) for x in _env("REPLY_POST_HOURS", "9-21").split("-", 1))
