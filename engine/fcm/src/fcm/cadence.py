"""Deterministic cadence rules: who is due for what, today.

Pure functions only — no network, no clock reads (callers pass `today`) — so the
same logic drives the live daily sweep, the demo simulation, and the tests.

Cadence (config/cadence.json, defaults in config.DEFAULT_CADENCE):
  * every affiliate gets a touch every 14 days, alternating SMS and email
  * an offer goes out once every 30 days
  * silent >= 45 days  -> lifecycle `aff:quiet`
  * silent >= 60 days  -> a PERSONAL check-in drafted for the manager to approve
  * silent >= 90 days  -> `aff:dormant` + the reactivation sequence
  * silent >= 180 days -> `aff:dead` + the dead-lead campaign every 90 days
  * a conversation that says "check back with me on X" sets next_touch_date,
    which beats every other rule on that day
  * a partner waiting on their reactivation kickoff (`fcm:kickoff-pending`) or on a reply to it
    (`fcm:kickoff-sent`) gets no bulk cadence: the kickoff is their next touch
"Silent" means no reply and no deal since max(last_reply_date, last_deal_date, join_date).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from typing import Any

LIFECYCLE_TAGS = (
    "aff:applied",
    "aff:onboarding",
    "aff:active",
    "aff:producing",
    "aff:quiet",
    "aff:dormant",
    "aff:dead",
    "aff:reactivated",
)
DNC_TAG = "aff:dnc"

TEST_CONTACT_TAG = "fcm:test-contact"
SOURCE_PREFIX = "src:"
KICKOFF_PENDING = "fcm:kickoff-pending"
KICKOFF_SENT = "fcm:kickoff-sent"
KICKOFF_DONE = "fcm:kickoff-done"
NO_EMAIL_TAG = "aff:no-email"  # opted out of email only; texts are still allowed
WRONG_NUMBER_TAG = "aff:wrong-number"  # no texts to this number until someone fixes it
NOT_INTERESTED_TAG = "aff:not-interested"  # said no thanks: no kickoff nudges or reactivation texts
TIERS = ("Platinum", "Gold", "Silver", "Bronze")

# SMS is billed per segment. One character outside the GSM-7 set (an em dash, a curly quote) switches the whole
# message to UCS-2: 70 characters per segment instead of 160, so a 160-character text bills as 3 segments.
_GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "ÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
_GSM7_EXT = set("^{}\\[~]|€")  # allowed, but each counts as two characters
_SMS_PLAIN = {"\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
              "\u2026": "...", "\u00a0": " ", "\u2022": "-", "\u2032": "'", "\u2033": '"'}


def sms_normalize(text: str) -> str:
    """Swap the usual typographic characters for GSM-7 equivalents so a text bills at 160 chars/segment."""
    return "".join(_SMS_PLAIN.get(ch, ch) for ch in text)


def sms_segments(text: str) -> dict[str, Any]:
    """Encoding and billed segment count for one SMS body."""
    if all(ch in _GSM7 or ch in _GSM7_EXT for ch in text):
        units = sum(2 if ch in _GSM7_EXT else 1 for ch in text)
        return {"encoding": "GSM-7", "units": units, "segments": 1 if units <= 160 else -(-units // 153)}
    units = len(text.encode("utf-16-le")) // 2
    return {"encoding": "UCS-2", "units": units, "segments": 1 if units <= 70 else -(-units // 67)}


# kind -> (mode, workflow key used for bulk enrollment, priority; lower runs first)
ACTION_KINDS: dict[str, tuple[str, str, int]] = {
    "kickoff": ("kickoff", "", 5),
    "scheduled_followup": ("personal", "", 10),
    "personal_checkin": ("personal", "", 20),
    "onboarding": ("bulk", "onboarding", 25),
    "dormant_reactivation": ("bulk", "dormant_reactivation", 30),
    "monthly_offer": ("bulk", "monthly_offer", 40),
    "biweekly_touch": ("bulk", "biweekly_touch", 50),
    "dead_reactivation": ("bulk", "dead_reactivation", 60),
}


def parse_day(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if text.isdigit() and len(text) >= 12:  # GHL DATE fields can come back as epoch millis
        return datetime.fromtimestamp(int(text) / 1000, UTC).date()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


@dataclass
class Affiliate:
    id: str
    name: str
    first_name: str
    email: str
    phone: str
    tags: list[str]
    fields: dict[str, Any]
    dnd: bool = False

    @property
    def source(self) -> str:
        explicit = str(self.fields.get("source") or "").strip()
        if explicit:
            return explicit
        for tag in self.tags:
            if tag.startswith(SOURCE_PREFIX):
                return tag[len(SOURCE_PREFIX):]
        return "unknown"

    @property
    def lifecycle(self) -> str:
        for tag in self.tags:
            if tag in LIFECYCLE_TAGS:
                return tag
        return ""

    @property
    def is_dnc(self) -> bool:
        return self.dnd or DNC_TAG in self.tags

    @property
    def no_email(self) -> bool:
        return NO_EMAIL_TAG in self.tags

    @property
    def sms_blocked(self) -> bool:
        return WRONG_NUMBER_TAG in self.tags

    @property
    def is_test_contact(self) -> bool:
        return TEST_CONTACT_TAG in self.tags

    @property
    def tier(self) -> str:
        value = str(self.fields.get("tier") or "").strip()
        if value:
            return value
        for tag in self.tags:
            if tag.startswith("tier:"):
                return next((t for t in TIERS if t.lower() == tag[5:]), tag[5:].title())
        return ""

    def day(self, key: str) -> date | None:
        return parse_day(self.fields.get(key))

    @property
    def deals_submitted(self) -> int:
        try:
            return int(float(self.fields.get("deals_submitted") or 0))
        except (TypeError, ValueError):
            return 0

    def last_engagement(self) -> date | None:
        days = [d for d in (self.day("last_reply_date"), self.day("last_deal_date"), self.day("join_date")) if d]
        return max(days) if days else None

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "lifecycle": self.lifecycle,
            "deals_submitted": self.deals_submitted,
            "last_deal_date": self.fields.get("last_deal_date") or "",
            "last_reply_date": self.fields.get("last_reply_date") or "",
            "last_touch_date": self.fields.get("last_touch_date") or "",
            "next_touch_date": self.fields.get("next_touch_date") or "",
            "cadence_note": self.fields.get("cadence_note") or "",
            "niche": self.fields.get("niche") or "",
            "test_contact": self.is_test_contact,
        }


def affiliate_from_contact(contact: dict[str, Any], field_ids: dict[str, str]) -> Affiliate:
    """Normalize a GHL contact (live or mock) into an Affiliate."""
    by_id = {v: k for k, v in field_ids.items()}
    fields: dict[str, Any] = {}
    for item in contact.get("customFields") or contact.get("customField") or []:
        key = by_id.get(item.get("id", ""))
        if key:
            fields[key] = item.get("value", item.get("fieldValue", item.get("field_value")))
    first = (contact.get("firstName") or "").strip()
    last = (contact.get("lastName") or "").strip()
    name = (contact.get("contactName") or f"{first} {last}").strip() or contact.get("email") or contact.get("id", "")
    return Affiliate(
        id=contact.get("id", ""),
        name=name,
        first_name=first or name.split(" ")[0],
        email=contact.get("email") or "",
        phone=contact.get("phone") or "",
        tags=[t for t in (contact.get("tags") or []) if isinstance(t, str)],
        fields=fields,
        dnd=bool(contact.get("dnd")),
    )


@dataclass
class DueItem:
    contact_id: str
    name: str
    kind: str
    mode: str
    channel: str
    reason: str
    priority: int
    workflow_key: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Evaluation:
    affiliate: Affiliate
    target_lifecycle: str
    days_silent: int | None
    days_since_touch: int | None
    due: list[DueItem]

    @property
    def lifecycle_change(self) -> tuple[str, str] | None:
        current = self.affiliate.lifecycle
        if self.target_lifecycle and self.target_lifecycle != current:
            return (current, self.target_lifecycle)
        return None


def _next_channel(aff: Affiliate) -> str:
    preferred = str(aff.fields.get("preferred_channel") or "").lower()
    if preferred in {"sms", "email"}:
        return preferred
    last = str(aff.fields.get("last_touch_channel") or "").lower()
    if last == "sms":
        return "email" if aff.email else "sms"
    if last == "email":
        return "sms" if aff.phone else "email"
    return "email" if aff.email else "sms"


def target_lifecycle(aff: Affiliate, today: date, rules: dict[str, Any]) -> tuple[str, int | None]:
    current = aff.lifecycle
    if current in {"aff:applied", "aff:onboarding"}:
        joined = aff.day("join_date")
        onboarding_days = int(rules.get("onboarding_days", 14))
        if current == "aff:applied" or joined is None or (today - joined).days < onboarding_days:
            return current, None
        current = "aff:active"  # onboarding window is over; judge them like everyone else
    engaged = aff.last_engagement()
    silent = (today - engaged).days if engaged else None
    last_deal = aff.day("last_deal_date")
    if last_deal and (today - last_deal).days <= 30:
        return "aff:producing", silent
    if current == "aff:producing":
        current = "aff:active"  # the 30-day deal window lapsed; judge them on silence like everyone else
    if silent is None:
        return current or "aff:active", None
    if silent >= rules["dead_after_days"]:
        return "aff:dead", silent
    if silent >= rules["dormant_after_days"]:
        return "aff:dormant", silent
    if silent >= rules["quiet_after_days"]:
        return "aff:quiet", silent
    if current in {"aff:dormant", "aff:dead", "aff:quiet"}:
        return "aff:reactivated", silent
    if current == "aff:reactivated" and silent > rules["biweekly_touch_days"]:
        return "aff:active", silent
    return current or "aff:active", silent


def evaluate(aff: Affiliate, today: date, rules: dict[str, Any]) -> Evaluation:
    lifecycle, silent = target_lifecycle(aff, today, rules)
    last_touch = aff.day("last_touch_date")
    since_touch = (today - last_touch).days if last_touch else None
    due: list[DueItem] = []
    if aff.is_dnc:
        return Evaluation(aff, lifecycle, silent, since_touch, due)

    def add(kind: str, reason: str, **context: Any) -> None:
        mode, workflow_key, priority = ACTION_KINDS[kind]
        due.append(DueItem(aff.id, aff.name, kind, mode, _next_channel(aff), reason, priority,
                           workflow_key, context))

    touched_recently = since_touch is not None and since_touch < rules["biweekly_touch_days"]
    next_touch = aff.day("next_touch_date")
    if KICKOFF_PENDING in aff.tags or KICKOFF_SENT in aff.tags:
        # the kickoff track owns this partner until they reply or get their one nudge (fcm.kickoff)
        if next_touch and next_touch <= today:
            add("scheduled_followup", f"asked us to follow up on {next_touch.isoformat()}",
                cadence_note=aff.fields.get("cadence_note") or "")
        elif KICKOFF_PENDING in aff.tags:
            add("kickoff", "first personal text from their partner manager")
        due.sort(key=lambda item: item.priority)
        return Evaluation(aff, lifecycle, silent, since_touch, due)
    if next_touch and next_touch <= today:
        add("scheduled_followup", f"asked us to follow up on {next_touch.isoformat()}",
            cadence_note=aff.fields.get("cadence_note") or "")
    elif lifecycle == "aff:applied" or (lifecycle == "aff:onboarding" and not touched_recently):
        add("onboarding", "new affiliate — onboarding sequence")
    elif lifecycle == "aff:dead":
        if since_touch is None or since_touch >= rules["dead_reactivation_every_days"]:
            add("dead_reactivation", f"no reply or deal in {silent} days")
    elif lifecycle == "aff:dormant" and not touched_recently:
        if aff.deals_submitted > 0:
            add("personal_checkin", f"has sent {aff.deals_submitted} deal(s) but silent {silent} days")
        else:
            add("dormant_reactivation", f"silent {silent} days")
    elif silent is not None and silent >= rules["checkin_after_days"] and not touched_recently:
        add("personal_checkin", f"silent {silent} days — personal check-in")
    elif not touched_recently:
        last_offer = aff.day("last_offer_date")
        if last_offer is None or (today - last_offer).days >= rules["monthly_offer_days"]:
            add("monthly_offer", "monthly offer is due")
        else:
            add("biweekly_touch", "bi-weekly touch is due")
    due.sort(key=lambda item: item.priority)
    return Evaluation(aff, lifecycle, silent, since_touch, due)


def sweep(affiliates: list[Affiliate], today: date, rules: dict[str, Any]) -> dict[str, Any]:
    """Evaluate every affiliate and roll the results into a daily plan."""
    evaluations = [evaluate(a, today, rules) for a in affiliates]
    personal: list[DueItem] = []
    kickoff: list[DueItem] = []
    bulk: dict[str, list[DueItem]] = {}
    lifecycle_changes: list[dict[str, Any]] = []
    cohorts: dict[str, int] = {}
    for ev in evaluations:
        cohorts[ev.target_lifecycle or "unknown"] = cohorts.get(ev.target_lifecycle or "unknown", 0) + 1
        change = ev.lifecycle_change
        if change:
            lifecycle_changes.append({"contact_id": ev.affiliate.id, "name": ev.affiliate.name,
                                      "from": change[0], "to": change[1]})
        for item in ev.due:
            if item.mode == "personal":
                personal.append(item)
            elif item.mode == "kickoff":
                kickoff.append(item)
            else:
                bulk.setdefault(item.kind, []).append(item)

    def personal_rank(item: DueItem) -> tuple[int, int]:
        aff = next(e.affiliate for e in evaluations if e.affiliate.id == item.contact_id)
        return (item.priority, -aff.deals_submitted)

    personal.sort(key=personal_rank)
    cap = int(rules["daily_personal_touch_cap"])
    return {
        "date": today.isoformat(),
        "total_affiliates": len(affiliates),
        "cohorts": dict(sorted(cohorts.items())),
        "silent_30_plus": sum(1 for e in evaluations if (e.days_silent or 0) >= 30),
        "silent_90_plus": sum(1 for e in evaluations if (e.days_silent or 0) >= 90),
        "lifecycle_changes": lifecycle_changes,
        "personal_queue": [i.to_dict() for i in personal[:cap]],
        "personal_overflow": max(0, len(personal) - cap),
        "kickoff_due": len(kickoff),
        "bulk_queue": {kind: [i.to_dict() for i in items] for kind, items in sorted(bulk.items())},
        "bulk_counts": {kind: len(items) for kind, items in sorted(bulk.items())},
    }


# Carrier opt-out keywords (CTIA): a reply that is just one of these, in any case or punctuation, is an opt-out.
OPT_OUT_WORDS = {"stop", "stopall", "stop all", "unsubscribe", "cancel", "end", "quit", "revoke", "optout",
                 "opt out", "stop please", "please stop", "remove", "remove me"}
OPT_OUT_PHRASES = (" unsubscrib", " remove me ", " do not contact ", " don't text ", " dont text ", " opt out ",
                   " opt me out ", " stop texting ", " stop messaging ", " stop contacting ", " stop sending ",
                   " stopall ", " stop all ", " take me off ", " off your list ", " off this list ",
                   " don't contact ", " dont contact ", " do not text ", " lose my number ", " delete my number ",
                   " remove my number ", " no more texts ", " no more messages ", " quit texting ", " leave me alone ")
HELP_WORDS = {"help", "info", "help please"}
WRONG_NUMBER_PHRASES = (" wrong number ", " wrong person ", " not the right person ", " you have the wrong ",
                        " you've got the wrong ", " no one by that name ", " nobody by that name ", " new number ",
                        " don't know who this is ", " dont know who this is ")
NOT_INTERESTED_PHRASES = (" not interested ", " no thanks ", " no thank you ", " i'm good ", " im good ",
                          " closed my business ", " out of the business ", " retired ", " no longer in ",
                          " not doing this anymore ", " not doing that anymore ", " moved on ", " pass on this ",
                          " not for me ")  # the W4 Monday email's own words: "reply 'not for me'"
# "Is this a bot?" and the like. The agent never answers these: the named manager replies personally.
IDENTITY_PHRASES = (" is this a bot ", " are you a bot ", " is this a robot ", " are you a robot ", " is this ai ",
                    " are you ai ", " is this an ai ", " are you an ai ", " is this automated ", " is this an automated ",
                    " is this a real person ", " are you a real person ", " are you real ", " is this real ",
                    " am i talking to a ", " am i texting a ", " are you human ", " is this a human ",
                    " is this really ", " is this chatgpt ", " is this a computer ", " is this an auto ",
                    " real person or ", " a bot or ", " automated message ", " auto generated ", " autogenerated ")
# Intents that are not a reply to us at all: they never count toward reply rates, never reactivate a partner,
# and the model can't override them. The manager handles HELP and wrong numbers; STOP is final.
NON_REPLY_INTENTS = {"unsubscribe", "help", "wrong_number"}
NO_DRAFT_INTENTS = NON_REPLY_INTENTS | {"identity_question"}

_QUOTE_START = re.compile(r"^\s*(?:>|on .{3,120} wrote:?\s*$|-{2,}\s*original message|_{5,}|from:\s.+@|"
                          r"sent from my |get outlook for )", re.I | re.M)
_WEEKDAY = r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues?|wed|thu(?:rs?)?|fri)"
_CLOCK = r"\d{1,2}(?::\d\d)?\s*(?:am|pm)"
_QUAL = rf"(?:morning|afternoon|evening|(?:at|after|before|around)\s+\d{{1,2}}(?::\d\d)?(?:\s*(?:am|pm))?|{_CLOCK})"
_PROPOSED_TIME = re.compile(
    rf"\b(?:(?:this|next)\s+)?{_WEEKDAY}\b(?:\s+{_QUAL})?|\b(?:today|tomorrow|tonight)(?:\s+{_QUAL}|(?=\s+(?:works|is good|"
    rf"is fine|would work)\b))|\b{_CLOCK}\b|\b(?:this|tomorrow)\s+(?:morning|afternoon|evening)\b", re.I)
_YES = re.compile(r"^\W*(?:yes|yeah|yep|yup|sure|sounds good|let'?s do it|works for me|that works|i'?m in|ok(?:ay)?|"
                  r"definitely|absolutely|happy to|for sure|perfect|great)\b", re.I)
_WANTS_CALL = re.compile(r"\b(?:call me|give me a call|let'?s (?:talk|chat|hop on|jump on)|happy to (?:talk|chat|hop on)|"
                         r"down (?:to|for a) (?:talk|chat|call)|open to a call|free to talk|can talk)\b", re.I)
_SCHEDULING_Q = re.compile(r"\b(?:what time|when works|when are you|what day|how about|does .{1,30} work)\b", re.I)
_PREFERS_TEXT = re.compile(r"\b(?:text(?:ing)? (?:is|works) (?:best|better|easier)|prefer (?:to )?text|rather text|"
                           r"just text|can'?t (?:talk|do (?:a )?calls?)|no calls|not (?:big )?on (?:the )?phone|"
                           r"bad (?:on|with) (?:the )?phone)\b", re.I)
_WILL_SEND = re.compile(r"\b(?:(?:a|one|two|\d+) deals? (?:a|per|every) (?:month|week)|send(?:ing)? you (?:some )?deals|"
                        r"start sending|will send (?:you )?(?:some|deals|one)|plan(?:ning)? to send|"
                        r"(?:have|got) (?:some|a few) (?:in the )?pipeline)\b", re.I)
_DEFER = re.compile(r"\b(?:check back|not (?:a good|the best) time|not right now|slammed|swamped|buried|"
                    r"next (?:month|quarter|year)|after the (?:holidays|new year|first)|after tax season|"
                    r"in a (?:few|couple(?: of)?) (?:weeks|months)|later this (?:month|year)|busy (?:right now|today|this|season|at the moment))\b",
                    re.I)
# A reply that is only "later" (T8 and the W4 Monday email ask for exactly that). Anchored to the whole reply, so
# "I'll send it later today" is not a request to defer.
_LATER_ONLY = re.compile(r"^\W*(?:(?:maybe|ok|okay|sure|yes|yeah)\W+)?(?:later|not now)(?:\W+(?:please|pls|thanks|thank you))?\W*$", re.I)
_DEFER_SOFT = re.compile(r"\b(?:busy|follow up|reach (?:back )?out (?:later|again)|next week)\b", re.I)


def _words(*phrases: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(phrases) + r")\b", re.I)


_HAS_DEAL = re.compile(r"\b(?:deal for you|have a deal|got a deal|deal to send|deal to submit|client needs|"
                       r"client who needs|have a client|got a client|merchant|file for you|send you the file|"
                       r"send you a file|referral for you|needs funding|needs capital|looking for funding|"
                       r"needs about \$)", re.I)
_COMMISSION = _words("commissions?", "paid", "payouts?", "split", "comp", "compensation")
_SERVICES = (("funnel", _words("funnel", "landing page", "website"), "medium"),
             ("reactivation", _words(r"reactivat\w*", "old leads", "dead leads", "my list"), "medium"),
             ("social", _words("social", "content", "posts"), "low"),
             ("email_campaigns", _words("email campaigns?", "newsletter for me", "emails for"), "low"),
             ("crm_help", _words("crm", "go high level", "gohighlevel", "ghl", "pipeline"), "low"))
_QUESTION = re.compile(r"\?|\b(?:how do i|how to|question)\b", re.I)
_EVENT = _words("webinars?", "events?", "training")


def strip_quoted(text: str) -> str:
    """What the partner actually wrote: drop a quoted email thread, signature-app footer or forwarded copy, so
    an "unsubscribe" link in the quoted footer of our own email can't opt out someone who wrote "call me Tuesday"."""
    text = text or ""
    m = _QUOTE_START.search(text)
    return (text[: m.start()] if m and m.start() > 0 else text).strip()


def _plain(text: str) -> str:
    """Lowercase words only, padded with spaces, so "STOP." / "Stop!" / "is this a bot??" match cleanly."""
    return " " + re.sub(r"[^a-z0-9$']+", " ", (text or "").lower().replace("’", "'")).strip() + " "


def is_opt_out(text: str) -> bool:
    plain = _plain(strip_quoted(text))
    if plain.strip() in OPT_OUT_WORDS or any(k in plain for k in OPT_OUT_PHRASES):
        return True
    return " stop " in plain and len(plain.split()) <= 3  # "STOP please", "stop it"; not "I can stop by Friday"


def is_help(text: str) -> bool:
    return _plain(strip_quoted(text)).strip() in HELP_WORDS


def is_identity_question(text: str) -> bool:
    plain = _plain(strip_quoted(text))
    return any(k in plain for k in IDENTITY_PHRASES)


def proposed_time(text: str) -> str:
    """The day or time a partner offered ("Wednesday afternoon", "tomorrow at 3pm"), or ""."""
    m = _PROPOSED_TIME.search(strip_quoted(text))
    return m.group(0).strip() if m else ""


def reply_signals(text: str) -> dict[str, Any]:
    """What a reply tells us beyond its intent: a time they offered, a plain yes, a preference for texting,
    a picture with no words."""
    body = strip_quoted(text)
    return {"proposed_time": proposed_time(body), "affirmative": bool(_YES.search(body)),
            "prefers_text": bool(_PREFERS_TEXT.search(body)), "empty": not body.strip()}


def classify_reply(text: str) -> dict[str, Any]:
    """Keyword baseline for reply triage. The agent's model refines this; the baseline guarantees STOP, HELP,
    wrong numbers and "is this a bot?" are never missed, and gives the simulation a deterministic path.
    Order matters: what must never be missed first, then what the partner is offering (a deal, a time),
    and only then the catch-alls ("?" means a question only when nothing more specific matched)."""
    body = strip_quoted(text)
    plain = _plain(body)
    signals = reply_signals(body)

    def out(intent: str, urgency: str, **extra: Any) -> dict[str, Any]:
        return {"intent": intent, "urgency": urgency, **extra, **{k: v for k, v in signals.items() if v}}

    if is_opt_out(body):
        return out("unsubscribe", "high")
    if is_help(body):
        return out("help", "high")
    if is_identity_question(body):
        return out("identity_question", "high")
    if any(k in plain for k in WRONG_NUMBER_PHRASES):
        return out("wrong_number", "medium")
    # Offering a deal, not merely mentioning one: "when do I get paid on funded deals?" is a commission
    # question and "how do I submit a deal?" is a question — neither is new deal flow.
    if _HAS_DEAL.search(body):
        return out("has_deal", "high")
    if any(k in plain for k in NOT_INTERESTED_PHRASES):
        return out("not_interested", "low")
    if (_DEFER.search(body) or _LATER_ONLY.match(body.strip())) and not signals["proposed_time"]:  # "busy today, try Thursday?" offers Thursday
        return out("check_back_later", "low")
    if signals["proposed_time"] or _WANTS_CALL.search(body) or (signals["affirmative"] and _SCHEDULING_Q.search(body)):
        return out("book_call", "high")
    if _WILL_SEND.search(body):
        return out("will_send_deals", "high")
    if _COMMISSION.search(body):
        return out("commission_question", "medium")
    for service, pattern, urgency in _SERVICES:
        if pattern.search(body):
            return out("wants_service", urgency, service=service)
    if _DEFER_SOFT.search(body):
        return out("check_back_later", "low")
    if _QUESTION.search(body):
        return out("question", "medium")
    if _EVENT.search(body):
        return out("event_interest", "low")
    return out("general_reply", "low")
