"""YouTube, through the Data API v3: a reply under the lead's comment (or a comment on their video), a subscribe,
and the replies in that thread.

    POST https://oauth2.googleapis.com/token                    refresh token -> an access token
    POST /youtube/v3/comments?part=snippet                      a reply under a top-level comment (parentId)
    POST /youtube/v3/commentThreads?part=snippet                a new comment on the video, when the lead is the video
    POST /youtube/v3/subscriptions?part=snippet                 following = subscribing to their channel
    GET  /youtube/v3/comments?part=snippet&parentId=<thread>    what was said in the thread since our reply

The account is the channel whose refresh token this is (scripts/youtube_token.py, Justin signing in himself), with
the youtube.force-ssl scope. A comment url carries `lc=<comment id>`; a reply's id is `<thread>.<reply>`, and
YouTube only takes replies under the thread's top comment, so replies go there. quotaExceeded, a rate limit,
forbidden, 401 and 429 are Blocked; commentsDisabled or a deleted video is just this post.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
from typing import Any

from .. import config
from . import Blocked, Posted, PostError, Transport, http

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
_VIDEO = re.compile(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})")
STOP = {"quotaExceeded", "rateLimitExceeded", "userRateLimitExceeded", "forbidden", "insufficientPermissions",
        "dailyLimitExceeded", "ineligibleAccount"}


def where(url: str) -> tuple[str, str]:
    """(video id, top-level comment id or "") from a YouTube url."""
    video = _VIDEO.search(url or "")
    if not video:
        raise PostError(f"not a YouTube video url: {url[:80]}")
    lc = (urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("lc") or [""])[0]
    return video.group(1), lc.split(".")[0]


class YouTube:
    name = "youtube"

    def __init__(self, client_id: str, secret: str, refresh_token: str, transport: Transport | None = None,
                 clock=time.time):
        self.client_id, self.secret, self.refresh_token = client_id, secret, refresh_token
        self.transport, self.clock = transport or http, clock
        self._token, self._expires, self._channel = "", 0.0, ""
        self.account = "youtube channel"

    @classmethod
    def from_config(cls, transport: Transport | None = None) -> "YouTube":
        return cls(config.YOUTUBE_CLIENT_ID, config.YOUTUBE_CLIENT_SECRET, config.YOUTUBE_REFRESH_TOKEN, transport)

    def ready(self) -> tuple[bool, str]:
        missing = [n for n, v in (("YOUTUBE_CLIENT_ID", self.client_id), ("YOUTUBE_CLIENT_SECRET", self.secret),
                                  ("YOUTUBE_REFRESH_TOKEN", self.refresh_token)) if not v]
        return (False, "no YouTube channel yet: " + ", ".join(missing) + " not set") if missing else (True, "")

    # ------------------------------------------------------------------------------------------------ the calls
    def _access(self) -> str:
        if self._token and self.clock() < self._expires - 60:
            return self._token
        body = urllib.parse.urlencode({"client_id": self.client_id, "client_secret": self.secret,
                                       "refresh_token": self.refresh_token, "grant_type": "refresh_token"}).encode()
        code, text = self.transport("POST", TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body)
        data = _json(text)
        if code >= 400 or not data.get("access_token"):
            raise Blocked(f"Google refused the refresh token (HTTP {code} {data.get('error', '')})")
        self._token, self._expires = data["access_token"], self.clock() + float(data.get("expires_in") or 3600)
        return self._token

    def _call(self, method: str, path: str, params: dict[str, str], body: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self._access()}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
        code, text = self.transport(method, url, headers, json.dumps(body).encode() if body is not None else None)
        out = _json(text)
        if code < 400:
            return out
        reasons = [e.get("reason", "") for e in ((out.get("error") or {}).get("errors") or [])]
        if code in (401, 429) or any(r in STOP for r in reasons):
            raise Blocked(f"YouTube {path}: HTTP {code} {', '.join(reasons)}")
        if "subscriptionDuplicate" in reasons:
            return {"duplicate": True}
        raise PostError(f"YouTube {path}: HTTP {code} {', '.join(reasons) or text[:120]}")

    def _mine(self) -> str:
        if not self._channel:
            items = self._call("GET", "/channels", {"part": "id", "mine": "true"}).get("items") or []
            self._channel = items[0]["id"] if items else ""
        return self._channel

    # ------------------------------------------------------------------------------------------------ the driver
    def reply(self, lead: dict[str, Any], text: str, parent: str = "") -> Posted:
        video, lc = where(lead.get("url") or "")
        thread = (parent or lc).split(".")[0]
        if thread:
            got = self._call("POST", "/comments", {"part": "snippet"},
                             {"snippet": {"parentId": thread, "textOriginal": text}})
            ours = got.get("id") or ""
        else:
            got = self._call("POST", "/commentThreads", {"part": "snippet"},
                             {"snippet": {"videoId": video, "topLevelComment": {"snippet": {"textOriginal": text}}}})
            thread = ours = got.get("id") or ""
        if not ours:
            raise PostError("YouTube took the comment but returned no id")
        return Posted(ref=f"{thread}:{ours}", url=f"https://www.youtube.com/watch?v={video}&lc={ours}")

    def follow(self, lead: dict[str, Any]) -> str:
        video, lc = where(lead.get("url") or "")
        if lc:
            items = self._call("GET", "/comments", {"part": "snippet", "id": lc}).get("items") or []
            channel = ((((items[0].get("snippet") or {}).get("authorChannelId")) or {}).get("value")) if items else ""
        else:
            items = self._call("GET", "/videos", {"part": "snippet", "id": video}).get("items") or []
            channel = (items[0].get("snippet") or {}).get("channelId") if items else ""
        if not channel or channel == self._mine():
            return ""
        self._call("POST", "/subscriptions", {"part": "snippet"},
                   {"snippet": {"resourceId": {"kind": "youtube#channel", "channelId": channel}}})
        return channel

    def replies(self, ref: str, since: str = "") -> list[dict[str, Any]]:
        thread, _, ours = ref.partition(":")
        if not thread:
            return []
        items = self._call("GET", "/comments", {"part": "snippet", "parentId": thread, "maxResults": "100",
                                                "textFormat": "plainText"}).get("items") or []
        mine, out = self._mine(), []
        for c in items:
            s = c.get("snippet") or {}
            channel = (s.get("authorChannelId") or {}).get("value") or ""
            if c.get("id") == ours or (mine and channel == mine) or (since and (s.get("publishedAt") or "") <= since):
                continue
            out.append({"id": c.get("id"), "author": s.get("authorDisplayName") or "", "author_id": channel,
                        "text": s.get("textOriginal") or s.get("textDisplay") or "", "at": s.get("publishedAt")})
        return out


def _json(text: str) -> Any:
    try:
        return json.loads(text) if text and text.strip() else {}
    except ValueError:
        return {}
