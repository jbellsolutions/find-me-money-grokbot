"""The platforms the auto-poster (poster.py) replies on. One driver per platform, all with the same four calls:

    ready()                         (True, "") when it holds an account it can post from, else (False, why)
    reply(lead, text, parent="")    post `text` in the lead's own thread (under `parent`, a comment of theirs, when
                                    given); returns Posted(ref, url). Raises Blocked or PostError
    follow(lead)                    follow the person who asked; returns what it followed, "" when it can't tell who
    replies(ref, since)             what was said under one of our posts after `since` (UTC, ...Z):
                                    [{id, author, author_id, text, at}]

Blocked means the platform said stop (a rate limit, a captcha, a warning, a 403): the poster stops that platform
for the rest of the day and says so. It never retries around one and never solves a captcha. PostError means this
one post can't go (a deleted or locked thread); the next lead is tried.

Reddit and YouTube post through their official APIs with a refresh token Justin made by signing in himself
(scripts/reddit_token.py, scripts/youtube_token.py). Facebook posts from a Chrome window on Justin's Mac signed in as
his own account (facebook.py), run by the Mac's browser lane (mac_lane.py), never from the Orgo computer. Every
other platform needs a signed-in browser account nobody has set up yet: those drivers only say so, so their leads
show as waiting on an account.
All HTTP goes through a transport the tests replace; no driver prints a token.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .. import config

# (method, url, headers, body bytes or None) -> (HTTP status, response text)
Transport = Callable[[str, str, dict, bytes | None], tuple[int, str]]
USER_AGENT = "pinnacle-reply-agent/0.1"
BROWSER = ("facebook", "tiktok", "skool", "instagram", "linkedin", "forum", "web")


class Blocked(RuntimeError):
    """The platform said stop: the poster stops it for the day."""


class PostError(RuntimeError):
    """This post can't go; the platform is fine."""


class Unconfirmed(PostError):
    """It was sent but didn't show where it should. It may be out, so it's never sent again, and the platform
    stops for the day so a person can look."""


@dataclass
class Posted:
    ref: str  # what the driver needs later to read replies under it
    url: str = ""


def http(method: str, url: str, headers: dict, data: bytes | None) -> tuple[int, str]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except urllib.error.URLError as exc:
        raise PostError(f"unreachable: {exc.reason}") from exc


def same_person(a: str | None, b: str | None) -> bool:
    """Whether two author names are one person: "u/Jane_D", "@jane_d" and "jane_d" all match."""
    def norm(x: str | None) -> str:
        x = (x or "").strip().lower()
        for prefix in ("/u/", "u/", "@"):
            x = x.removeprefix(prefix)
        return x
    return bool(norm(a)) and norm(a) == norm(b)


class NoAccount:
    """A platform that needs a signed-in browser account nobody has set up yet."""

    def __init__(self, platform: str, why: str = ""):
        self.name, self.account = platform, ""
        self.why = why or f"no signed-in account for {platform} yet"

    def ready(self) -> tuple[bool, str]:
        return False, self.why

    def reply(self, lead: dict[str, Any], text: str, parent: str = "") -> Posted:
        raise PostError(self.ready()[1])

    def follow(self, lead: dict[str, Any]) -> str:
        raise PostError(self.ready()[1])

    def replies(self, ref: str, since: str = "") -> list[dict[str, Any]]:
        return []


def drivers(transport: Transport | None = None) -> dict[str, Any]:
    """Every platform's driver, built from the settings (config.py)."""
    from .reddit import Reddit
    from .youtube import YouTube
    out: dict[str, Any] = {p: NoAccount(p) for p in BROWSER}
    if config.FACEBOOK_BROWSER:
        from .facebook import Facebook
        out["facebook"] = Facebook.from_config()
    else:
        out["facebook"] = NoAccount("facebook", "posts from the browser lane on Justin's Mac (reply-agent-mac), "
                                                "not from this computer")
    out["reddit"] = Reddit.from_config(transport)
    out["youtube"] = YouTube.from_config(transport)
    return out
