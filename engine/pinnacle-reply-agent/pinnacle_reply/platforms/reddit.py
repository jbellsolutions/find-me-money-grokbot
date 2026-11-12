"""Reddit, through its official API: a comment in the lead's thread, a follow, and the replies under our comment.

    POST https://www.reddit.com/api/v1/access_token   refresh token -> an hour's access token
    POST https://oauth.reddit.com/api/comment          thing_id (t3_ post or t1_ comment) + text
    POST https://oauth.reddit.com/api/subscribe        sr_name=u_<author>: following a person is subscribing to them
    GET  https://oauth.reddit.com/comments/<post>?comment=<ours>&depth=2   what was said under our comment

The account is the one whose refresh token this is (scripts/reddit_token.py, Justin signing in himself). Reddit's
rules ask for a user agent naming the app and that account. A RATELIMIT error, 403 or 429 is Blocked.
"""

from __future__ import annotations

import base64
import json
import re
import time
import urllib.parse
from typing import Any

from .. import config
from . import Blocked, Posted, PostError, Transport, http

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
_POST = re.compile(r"(?:/comments/|redd\.it/)([a-z0-9]+)", re.I)
_COMMENT = re.compile(r"/comments/[a-z0-9]+/[^/?#]*/([a-z0-9]+)", re.I)
# Errors that mean the account should stop for the day, not just skip this thread
STOP = {"RATELIMIT", "BANNED_FROM_SUBREDDIT", "USER_REQUIRED", "SUBREDDIT_NOTALLOWED"}


def thing(url: str) -> tuple[str, str]:
    """(post fullname t3_, the thing to reply to): the comment when the url is a comment's permalink, else the post."""
    post = _POST.search(url or "")
    if not post:
        raise PostError(f"not a Reddit thread url: {url[:80]}")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    permalink = _COMMENT.search(url)
    comment = (q.get("comment") or [""])[0] or (permalink.group(1) if permalink else "")
    return f"t3_{post.group(1)}", f"t1_{comment}" if comment else f"t3_{post.group(1)}"


class Reddit:
    name = "reddit"

    def __init__(self, client_id: str, secret: str, refresh_token: str, username: str,
                 transport: Transport | None = None, clock=time.time):
        self.client_id, self.secret, self.refresh_token = client_id, secret, refresh_token
        self.account = username.removeprefix("u/")
        self.transport, self.clock = transport or http, clock
        self._token, self._expires = "", 0.0
        self.agent = f"python:pinnacle-reply-agent:0.1 (by /u/{self.account or 'unknown'})"

    @classmethod
    def from_config(cls, transport: Transport | None = None) -> "Reddit":
        return cls(config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET, config.REDDIT_REFRESH_TOKEN,
                   config.REDDIT_USERNAME, transport)

    def ready(self) -> tuple[bool, str]:
        missing = [n for n, v in (("REDDIT_CLIENT_ID", self.client_id), ("REDDIT_CLIENT_SECRET", self.secret),
                                  ("REDDIT_REFRESH_TOKEN", self.refresh_token), ("REDDIT_USERNAME", self.account)) if not v]
        return (False, "no Reddit account yet: " + ", ".join(missing) + " not set") if missing else (True, "")

    # ------------------------------------------------------------------------------------------------ the calls
    def _access(self) -> str:
        if self._token and self.clock() < self._expires - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.secret}".encode()).decode()
        body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": self.refresh_token}).encode()
        code, text = self.transport("POST", TOKEN_URL, {"Authorization": f"Basic {basic}", "User-Agent": self.agent,
                                                        "Content-Type": "application/x-www-form-urlencoded"}, body)
        data = _json(text)
        if code >= 400 or not data.get("access_token"):
            raise Blocked(f"Reddit refused the refresh token (HTTP {code} {data.get('error', '')})")
        self._token, self._expires = data["access_token"], self.clock() + float(data.get("expires_in") or 3600)
        return self._token

    def _call(self, method: str, path: str, form: dict[str, str] | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self._access()}", "User-Agent": self.agent}
        data = None
        if form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urllib.parse.urlencode(form).encode()
        code, text = self.transport(method, API + path, headers, data)
        if code in (401, 403, 429):
            raise Blocked(f"Reddit {path}: HTTP {code}")
        if code == 404:
            raise PostError(f"Reddit {path}: not found (deleted or private)")
        if code >= 400:
            raise PostError(f"Reddit {path}: HTTP {code} {text[:120]}")
        out = _json(text)
        errors = ((out.get("json") or {}).get("errors") or []) if isinstance(out, dict) else []
        names = [str(e[0]).upper() for e in errors if e]
        if any(n in STOP or "CAPTCHA" in n for n in names):
            raise Blocked(f"Reddit {path}: {', '.join(names)}")
        if names:
            raise PostError(f"Reddit {path}: {', '.join(names)}")  # e.g. a locked or archived thread
        return out

    # ------------------------------------------------------------------------------------------------ the driver
    def reply(self, lead: dict[str, Any], text: str, parent: str = "") -> Posted:
        post, target = thing(lead.get("url") or "")
        out = self._call("POST", "/api/comment", {"api_type": "json", "thing_id": parent or target, "text": text})
        things = ((out.get("json") or {}).get("data") or {}).get("things") or []
        data = (things[0].get("data") or {}) if things else {}
        name = data.get("name") or (f"t1_{data['id']}" if data.get("id") else "")
        if not name:
            raise PostError("Reddit took the comment but returned no id")
        link = data.get("link_id") or post
        url = "https://www.reddit.com" + data["permalink"] if data.get("permalink") else ""
        return Posted(ref=f"{link}:{name}", url=url)

    def follow(self, lead: dict[str, Any]) -> str:
        who = (lead.get("author") or "").strip().removeprefix("/u/").removeprefix("u/")
        if not who or who in ("[deleted]", self.account):
            return ""
        self._call("POST", "/api/subscribe", {"action": "sub", "sr_name": f"u_{who}"})
        return f"u/{who}"

    def replies(self, ref: str, since: str = "") -> list[dict[str, Any]]:
        """Replies directly under our comment: all came after it, so `since` isn't needed here."""
        link, _, ours = ref.partition(":")
        if not ours.startswith("t1_"):
            return []
        data = self._call("GET", f"/comments/{link.removeprefix('t3_')}?comment={ours.removeprefix('t1_')}"
                                 "&depth=2&limit=50&raw_json=1")
        out: list[dict[str, Any]] = []
        listing = data[1] if isinstance(data, list) and len(data) > 1 else {}
        for top in ((listing.get("data") or {}).get("children") or []):
            under = ((top.get("data") or {}).get("replies") or {})
            for child in ((under.get("data") or {}).get("children") or []) if isinstance(under, dict) else []:
                d = child.get("data") or {}
                if child.get("kind") == "t1" and d.get("author") and d.get("author") != self.account:
                    out.append({"id": d.get("name") or f"t1_{d.get('id')}", "author": d["author"],
                                "author_id": d.get("author_fullname") or "", "text": d.get("body") or "",
                                "at": d.get("created_utc")})
        return out


def _json(text: str) -> Any:
    try:
        return json.loads(text) if text and text.strip() else {}
    except ValueError:
        return {}
