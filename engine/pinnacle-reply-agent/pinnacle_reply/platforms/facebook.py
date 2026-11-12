"""Facebook, through a Chrome window on Justin's Mac signed in as his own account: a comment on the lead's group
post, a reply under their answer, a follow, and the replies under our comment. Meta has no API for any of it.

The browser is Google Chrome with its own profile folder (FACEBOOK_PROFILE_DIR, under ~/Library/Application Support,
never Justin's everyday profile and never iCloud). `reply-agent-mac open` starts it on facebook.com; Justin signs in
there himself and joins the groups. The agent drives that same window over Chrome's DevTools port on 127.0.0.1.
It types the way a person does and adds nothing that hides it's a script.

What it reads on the page, and what that means:
  Blocked (Facebook stops for the day): a login page, a checkpoint, a captcha, "temporarily blocked", "you can't
    use this feature", a posting limit, a locked or restricted account. It never solves or works around one.
  PostError (this lead is skipped): the post is gone or private, the account isn't in the group ("Join"),
    comments are off, or the comment box isn't there.
  Unconfirmed: the comment was sent but our text didn't show under the post. It may have gone out (a group that
    holds comments for its admins), so it's never sent again; Facebook stops for the day and Justin checks the link.
"""

from __future__ import annotations

import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable

from .. import config
from . import Blocked, Posted, PostError, Unconfirmed

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HOME_URL = "https://www.facebook.com/"
# The comment box under a post, and the reply box under a comment, by their accessible names
COMMENT_BOX = re.compile(r"^(write a (public )?(comment|answer)|(comment|answer) as |write an answer|leave a comment)",
                         re.I)  # a question post's box is "Answer as Justin"
REPLY_BOX = re.compile(r"^(reply to |write a reply|reply as )", re.I)
# The group's join button: "Join" beside the group's name on a post, "Join group" on the group's page
JOIN = re.compile(r"^join( this)?( group)?$", re.I)
STOP_URL = ("/checkpoint", "/login", "login.php", "/two_step_verification", "/captcha")
STOP_TEXT = ("you're temporarily blocked", "you’re temporarily blocked", "you can't use this feature",
             "you can’t use this feature", "we limit how often", "your account has been locked",
             "your account is restricted", "confirm your identity", "enter the characters you see",
             "suspect automated", "security check", "log in to facebook", "log into facebook")
GONE_TEXT = ("this content isn't available", "this content isn’t available", "content isn't available right now",
             "content isn’t available right now", "this page isn't available", "this page isn’t available")
CLOSED_TEXT = ("commenting has been turned off", "turned off commenting", "comments have been turned off")
_POST_ID = re.compile(r"/(?:posts|permalink)/(\d+)")
_GROUP = re.compile(r"/groups/([^/?#]+)")


def post_id(url: str) -> str:
    m = _POST_ID.search(url or "")
    return m.group(1) if m else ""


def group(url: str) -> str:
    """The group's id or name from a post url: what Justin joins."""
    m = _GROUP.search(url or "")
    return m.group(1) if m else ""


def query(url: str, name: str) -> str:
    return (urllib.parse.parse_qs(urllib.parse.urlparse(url or "").query).get(name) or [""])[0]


def snippet(text: str, n: int = 48) -> str:
    """The start of a comment's first line as Facebook shows it: whitespace folded, cut on a word."""
    flat = " ".join((text or "").strip().split("\n")[0].split())
    return flat if len(flat) <= n else flat[:n].rsplit(" ", 1)[0]


def person(author: str | None) -> str:
    """The lead's author as a Facebook person id, or "" when the scraper only kept a post token (pfbid...)."""
    a = (author or "").strip()
    return a if a.isdigit() else ""


class Facebook:
    name = "facebook"

    def __init__(self, port: int, profile_dir: Path, account_label: str = "", connect: Callable | None = None,
                 wait_ms: int = 4000, confirm_ms: int = 20000, launch: bool = True, type_delay_ms: int = 12):
        self.port, self.profile_dir, self.label = port, Path(profile_dir), account_label
        self._connect, self.wait_ms, self.confirm_ms, self.launch_ok = connect, wait_ms, confirm_ms, launch
        self.type_delay_ms = type_delay_ms
        self._pw = self._browser = self._context = None
        self.account, self.user_id = "", ""

    @classmethod
    def from_config(cls) -> "Facebook":
        return cls(config.FACEBOOK_PORT, config.FACEBOOK_PROFILE_DIR, config.FACEBOOK_ACCOUNT)

    # ------------------------------------------------------------------------------------------- the window
    def open_window(self, url: str = HOME_URL) -> bool:
        """Start the profile's Chrome window if it isn't open. True when it was started."""
        if self._reachable():
            if not self._tabs():  # Chrome is running with every window closed: give Justin one back
                self._new_tab(url)
            return False
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen([CHROME, f"--user-data-dir={self.profile_dir}", f"--remote-debugging-port={self.port}",
                          "--no-first-run", "--no-default-browser-check", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(40):
            if self._reachable():
                return True
            time.sleep(0.5)
        raise PostError("Chrome didn't open its DevTools port")

    def _reachable(self) -> bool:
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=2) as r:
                return r.status == 200
        except OSError:
            return False

    def _tabs(self) -> int:
        """The window's open tabs. Chrome with none left refuses a DevTools connection."""
        import json
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=2) as r:
                return sum(1 for t in json.load(r) if t.get("type") == "page")
        except (OSError, ValueError):
            return 0

    def _new_tab(self, url: str = "about:blank") -> None:
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/new?{url}", method="PUT")
        try:
            urllib.request.urlopen(req, timeout=5).close()
        except OSError as exc:
            raise PostError(f"couldn't open a tab in the Facebook window: {exc}"[:200]) from exc

    def context(self):
        if self._context is not None:
            return self._context
        if self._connect is not None:  # tests: a browser context of their own, kept open by the test
            self._context = self._connect()
            return self._context
        if not self._reachable():
            if not self.launch_ok:
                raise PostError("the Facebook window isn't open: reply-agent-mac open")
            self.open_window()
        if not self._tabs():
            self._new_tab()
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}")
            self._context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        except BaseException:
            self.close()
            raise
        return self._context

    def close(self) -> None:
        """Let go of the window; Chrome itself stays open and signed in."""
        try:
            if self._pw is not None:
                self._pw.stop()
        finally:
            self._pw = self._browser = self._context = None

    def ready(self) -> tuple[bool, str]:
        try:
            cookies = self.context().cookies(HOME_URL)
        except PostError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001 - any browser failure means not ready, never a crash
            return False, f"the Facebook window can't be reached: {exc}"[:200]
        uid = next((c["value"] for c in cookies if c.get("name") == "c_user" and c.get("value")), "")
        if not uid:
            return False, "the Facebook window isn't signed in: Justin signs in once (reply-agent-mac open)"
        self.user_id, self.account = uid, self.label or f"facebook user {uid}"
        return True, ""

    # ------------------------------------------------------------------------------------------- reading a page
    def _page(self, url: str):
        page = self.context().new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(self.wait_ms)
        except Exception as exc:  # noqa: BLE001
            page.close()
            raise PostError(f"the page didn't load: {exc}"[:200]) from exc
        return page

    @staticmethod
    def _text(page) -> str:
        try:
            return page.locator("body").inner_text(timeout=5000).lower()
        except Exception:  # noqa: BLE001
            return ""

    def _stop_check(self, page) -> None:
        """Raise Blocked when Facebook says stop. Called on every page before anything is typed."""
        url = page.url.lower()
        if any(s in url for s in STOP_URL):
            raise Blocked(f"facebook: {urllib.parse.urlparse(page.url).path or 'a login or checkpoint page'}")
        body = self._text(page)
        hit = next((s for s in STOP_TEXT if s in body), "")
        if hit or page.locator("iframe[src*='captcha' i]").count():
            raise Blocked(f"facebook: \"{hit or 'captcha'}\"")

    def inspect(self, url: str, keep: bool = False) -> dict[str, Any]:
        """Open a lead's post and say what a reply would meet there, typing nothing:
        {state: ready|not_member|gone|closed|no_box|wrong_post, group, page}. Blocked raises."""
        page = self._page(url)
        try:
            self._stop_check(page)
            out: dict[str, Any] = {"group": group(url), "url": page.url}
            body = self._text(page)
            want = post_id(url)
            if any(s in body for s in GONE_TEXT):
                out["state"] = "gone"
            elif want and want not in page.url and not page.locator(f"a[href*='{want}']").count():
                out["state"] = "wrong_post"
            else:
                has_box = self._box(page, COMMENT_BOX, wait_ms=2 * self.wait_ms) is not None
                if self._post_scope(page).get_by_role("button", name=JOIN).count():
                    # a public group shows its box to anyone; the comment only goes through for a member
                    out["state"] = "not_member"
                elif has_box:
                    out["state"] = "ready"
                elif any(s in body for s in CLOSED_TEXT):
                    out["state"] = "closed"
                else:
                    out["state"] = "no_box"
        except BaseException:
            page.close()
            raise
        if keep:
            out["page"] = page
        else:
            page.close()
        return out

    @staticmethod
    def _post_scope(page):
        """The post's own dialog when Facebook opens it over the group's feed, so the feed behind it isn't read."""
        dialog = page.locator("[role=dialog][aria-modal=true]")
        return dialog.last if dialog.count() else page

    @staticmethod
    def _box(page, name: re.Pattern, wait_ms: int = 0):
        box = page.get_by_role("textbox", name=name)
        if wait_ms and not box.count():  # the box comes in last, after the post and its comments
            try:
                box.first.wait_for(state="attached", timeout=wait_ms)
            except Exception:  # noqa: BLE001
                pass
        if box.count():
            return box.last if name is REPLY_BOX else box.first
        opener = page.get_by_role("button", name=re.compile(r"^(leave a comment|comment)$", re.I))
        if name is COMMENT_BOX and opener.count():
            opener.first.click()
            page.wait_for_timeout(1000)
            box = page.get_by_role("textbox", name=name)
            return box.first if box.count() else None
        return None

    # ------------------------------------------------------------------------------------------- posting
    def reply(self, lead: dict[str, Any], text: str, parent: str = "") -> Posted:
        url = lead.get("url") or ""
        if not post_id(url):
            raise PostError(f"not a Facebook post url: {url[:80]}")
        # a follow-up opens their answer's permalink, where Facebook shows it; a first reply opens the post
        seen = self.inspect(parent if parent.startswith("http") else url, keep=True)
        page = seen.pop("page", None)
        try:
            why = {"gone": "the post is gone or private", "wrong_post": "the link didn't open that post",
                   "not_member": f"not a member of group {seen['group']}: join it to reply",
                   "closed": "comments are off on this post", "no_box": "no comment box on this post"}
            if seen["state"] != "ready":
                raise PostError(why[seen["state"]])
            if parent:
                box = self._reply_box(page, parent)
            else:
                box = self._box(page, COMMENT_BOX)
            if box is None:
                raise PostError("the reply box didn't open")
            self._type(page, box, text)
            self._stop_check(page)
            return self._confirm(page, url, text, parent)
        finally:
            if page is not None:
                page.close()

    def _reply_box(self, page, parent: str):
        """Their comment (parent: its permalink or comment id), its Reply button, then the box under it."""
        cid = query(parent, "reply_comment_id") or query(parent, "comment_id") or parent
        link = page.locator(f"a[href*='comment_id={cid}']").first
        if not link.count():
            self._expand(page)
        if not link.count():
            raise PostError("their comment isn't showing on the post anymore")
        art = page.get_by_role("article").filter(has=link).last
        art.get_by_role("button", name=re.compile(r"^reply$", re.I)).first.click()
        page.wait_for_timeout(1000)
        return self._box(page, REPLY_BOX)

    def _type(self, page, box, text: str) -> None:
        box.click()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            page.keyboard.type(line, delay=self.type_delay_ms)
            if i < len(lines) - 1:
                page.keyboard.press("Shift+Enter")
        page.keyboard.press("Enter")

    def _confirm(self, page, url: str, text: str, parent: str) -> Posted:
        """Our comment, showing under the post, and its permalink. Sent but not showing is Unconfirmed."""
        want = snippet(text)
        mine = page.get_by_role("article").filter(has_text=want)
        try:
            mine.last.wait_for(state="visible", timeout=self.confirm_ms)
        except Exception as exc:  # noqa: BLE001
            raise Unconfirmed(f"sent, but it isn't showing under the post: check {url}") from exc
        art = mine.last
        links = [a.get_attribute("href") or "" for a in art.locator("a[href*='comment_id=']").all()]
        cid = next((query(h, "reply_comment_id") or query(h, "comment_id") for h in links if h), "")
        base = url.split("?")[0]
        if not cid:
            return Posted(ref=f"{base}#text={urllib.parse.quote(want)}", url=base)
        top = query(parent, "comment_id") if parent else ""
        q = {"comment_id": top or cid, **({"reply_comment_id": cid} if top else {})}
        link = f"{base}?{urllib.parse.urlencode(q)}"
        return Posted(ref=link, url=link)

    def follow(self, lead: dict[str, Any]) -> str:
        """Follow the person on their profile, when their profile offers Follow. "" when it doesn't."""
        pid = person(lead.get("author"))
        if not pid:
            return ""
        page = self._page(f"https://www.facebook.com/profile.php?id={pid}")
        try:
            self._stop_check(page)
            btn = page.get_by_role("button", name=re.compile(r"^follow$", re.I))
            if not btn.count():
                return ""
            btn.first.click()
            page.wait_for_timeout(1500)
            self._stop_check(page)
            return f"facebook:{pid}"
        finally:
            page.close()

    # ------------------------------------------------------------------------------------------- their answers
    def replies(self, ref: str, since: str = "") -> list[dict[str, Any]]:
        """What was said under our comment: each reply's id, author (their person id when the link shows it,
        else their name), text. Ours are left out. `since` isn't used: Facebook shows "2h", and the poster keeps
        the ids it has seen."""
        ours = query(ref, "reply_comment_id") or query(ref, "comment_id")
        if not ours:
            return []  # posted without a permalink: there's no thread of ours to read
        page = self._page(ref)
        base = ref.split("?")[0].split("#")[0]
        try:
            self._stop_check(page)
            self._expand(page)
            out = []
            for art in page.get_by_role("article").all():
                hrefs = [a.get_attribute("href") or "" for a in art.locator("a[href*='reply_comment_id=']").all()]
                rid = next((query(h, "reply_comment_id") for h in hrefs if query(h, "comment_id") == ours), "")
                if not rid or rid == ours:
                    continue
                who = self._author(art)
                if who["id"] and who["id"] == self.user_id:
                    continue
                out.append({"id": f"{base}?comment_id={ours}&reply_comment_id={rid}",  # where a follow-up goes
                            "author": who["id"] or who["name"], "author_id": who["id"],
                            "text": self._said(art, who["name"]), "at": ""})
            return out
        finally:
            page.close()

    @staticmethod
    def _expand(page) -> None:
        """Open the replies Facebook folds under a comment ("View 3 replies")."""
        for _ in range(3):
            more = page.get_by_role("button", name=re.compile(r"(view|see) (all |more |previous )?\d* ?repl", re.I))
            if not more.count():
                return
            more.first.click()
            page.wait_for_timeout(1500)

    @staticmethod
    def _author(art) -> dict[str, str]:
        for a in art.locator("a[href]").all():
            h = a.get_attribute("href") or ""
            m = re.search(r"/user/(\d+)|profile\.php\?id=(\d+)", h)
            name = (a.inner_text() or "").strip()
            if m and name:
                return {"id": m.group(1) or m.group(2), "name": name}
        label = art.get_attribute("aria-label") or ""
        m = re.match(r"^(?:reply|comment) by (.+?)(?: to .+)?(?: \d+ ?\w* ago)?$", label, re.I)
        return {"id": "", "name": m.group(1) if m else ""}

    @staticmethod
    def _said(art, name: str) -> str:
        parts = [t.strip() for t in art.locator("div[dir='auto']").all_inner_texts() if t.strip()]
        parts = [p for p in parts if p != name]
        return " ".join(parts)[:2000]
