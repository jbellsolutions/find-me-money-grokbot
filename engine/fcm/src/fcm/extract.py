"""Turn what a partner says into profile facts and commitments.

Two extractors share one interface, the same way reply triage pairs a keyword baseline with the model:
  * RuleExtractor   keyword and pattern rules. Deterministic: the simulation, the tests, and the floor
                    when no model is configured. It only keeps what the partner plainly said.
  * ModelExtractor  the drafting model (fcm.llm), validated against the profile schema, falling back to
                    the rules on any error.

    extract_text(text, partner)            -> {"facts": [...], "summary": str}
    extract_call(transcript, partner, us)  -> {"facts", "commitments", "summary"}
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from . import llm

STATES = ("Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia Hawaii Idaho "
          "Illinois Indiana Iowa Kansas Kentucky Louisiana Maine Maryland Massachusetts Michigan Minnesota "
          "Mississippi Missouri Montana Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania Tennessee Texas Utah "
          "Vermont Virginia Washington Wisconsin Wyoming").split() + ["New York", "New Jersey", "New Mexico",
                                                                     "New Hampshire", "North Carolina",
                                                                     "South Carolina", "North Dakota",
                                                                     "South Dakota", "Rhode Island", "West Virginia"]
NEEDS = [  # phrase -> what their clients need (also a product hub in the vault)
    (r"\bequipment\b", "equipment financing"), (r"\btrucks?\b|\btrailers?\b", "equipment financing"),
    (r"\bpayroll\b", "working capital"), (r"working capital|cash ?flow|slow season", "working capital"),
    (r"\binventory\b", "inventory financing"), (r"line of credit|\bLOC\b", "a line of credit"),
    (r"\bSBA\b", "SBA loans"), (r"expan|second location|new location|build-?out|remodel", "expansion capital"),
    (r"credit cards?|credit stacking|0% (?:intro|cards)", "business credit cards"),
    (r"\bstart-?ups?\b|just starting", "startup funding"), (r"\bMCA\b|merchant cash advance", "short-term funding"),
]
GROWTH = [(r"funnel|landing page", "a funnel page"), (r"old leads|dead leads|my list|reactivat", "lead reactivation"),
          (r"social|content|posts", "social content"), (r"email campaign|newsletter", "email campaigns"),
          (r"\bcrm\b|go ?high ?level|\bghl\b|pipeline", "CRM help"), (r"more leads|lead flow|referrals", "more leads")]
_END = (r"(?=[.!?\n]|,? (?:and|but|so) (?:i|we|they|my)\b|"
        r", (?:usually|typically|mostly|mainly|around|about|so|which|who|they|it'?s)\b|$)")


def _cap(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".,;:!?")


def _money(text: str) -> str:
    """The typical amount: one said with "usually/around/about/typically" wins over the first one mentioned."""
    amount = r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(k|K|m|M|million|thousand)?\b"
    m = (re.search(r"(?:usually|around|about|typically|average|avg)\s+(?:around\s+|about\s+)?" + amount, text, re.I)
         or re.search(amount, text))
    if not m:
        return ""
    unit = {"k": "k", "thousand": "k", "m": "M", "million": "M"}.get((m.group(2) or "").lower(), "")
    return f"around ${m.group(1)}{unit}"


def due_from(text: str, today: date) -> str:
    t = text.lower()
    if "tomorrow" in t:
        return (today + timedelta(days=1)).isoformat()
    if "today" in t or "tonight" in t:
        return today.isoformat()
    if "next week" in t:
        return (today + timedelta(days=7)).isoformat()
    for i, day in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday")):
        if day in t:
            ahead = (i - today.weekday()) % 7 or 7
            return (today + timedelta(days=ahead)).isoformat()
    return (today + timedelta(days=2)).isoformat()


class RuleExtractor:
    name = "rules"

    def extract_text(self, text: str, partner: dict[str, Any] | None = None) -> dict[str, Any]:
        t = " " + (text or "") + " "
        low = t.lower()
        facts: list[dict[str, str]] = []

        def add(slot: str, value: str) -> None:
            value = _cap(value)
            if value and len(value) > 2 and {"slot": slot, "value": value} not in facts:
                facts.append({"slot": slot, "value": value})

        for pat in (r"(?:my|our) clients are (?:mostly |mainly |usually |all )?([^.!?\n]{3,70}?)" + _END,
                    r"\bi (?:mostly |mainly |usually )?work with ([^.!?\n]{3,70}?)" + _END,
                    r"\b(?:mostly|mainly) (?:work with|serve|help) ([^.!?\n]{3,70}?)" + _END,
                    r"\bmost of my clients are ([^.!?\n]{3,70}?)" + _END):
            for m in re.finditer(pat, t, re.I):
                if not re.match(r"(?:in|from|based|located|all over|local)\b", m.group(1).strip(), re.I):
                    add("client_types", m.group(1))
        for pat, label in NEEDS:
            if re.search(pat, t, re.I):
                add("deal_types", label)
        if (money := _money(t)) and re.search(r"deal|need|looking|usually|typical|loan|funding|capital", low):
            add("deal_size", money)
        for pat in (r"\b(?:i'm|i am|we're|we are) (?:trying|looking|hoping|working|aiming) to ([^.!?\n]{5,90}?)" + _END,
                    r"\bmy goal (?:this year )?is to ([^.!?\n]{5,90}?)" + _END,
                    r"\bi want to ([^.!?\n]{5,90}?)" + _END,
                    r"\bi(?:'d| would) (?:love|like) to ([^.!?\n]{5,90}?)" + _END):
            for m in re.finditer(pat, t, re.I):
                add("goals", m.group(1))
        for pat in (r"\b(?:it would|that would|what would) (?:really )?help (?:is |me )?([^.!?\n]{5,90}?)" + _END,
                    r"\bi (?:could really use|could use|really need|need) (?:some |a |an )?(help with [^.!?\n]{4,80}?|"
                    r"[^.!?\n]{4,80}?)" + _END):
            for m in re.finditer(pat, t, re.I):
                add("needs", m.group(1))
        for pat, label in GROWTH:
            if re.search(pat, low) and re.search(r"\b(?:help|need|want|could use|looking for)\b", low):
                add("needs", label)
        for pat in (r"\bhaven'?t (?:sent|been sending)[^.!?\n]{0,25}? because ([^.!?\n]{5,90}?)" + _END,
                    r"\b(?:been|i'm|i am) (?:slammed|swamped|buried) (?:with |by )?([^.!?\n]{3,60}?)" + _END):
            for m in re.finditer(pat, t, re.I):
                add("blockers", m.group(1))
        if re.search(r"\b(?:text me|texting is (?:best|easier)|text is best|prefer text|just text|texts? (?:are|is) easier)\b", low):
            add("channel", "text")
        elif re.search(r"\b(?:call me|prefer a call|rather talk|phone is best|give me a call)\b", low):
            add("channel", "phone call")
        elif re.search(r"\b(?:email me|prefer email|email is best)\b", low):
            add("channel", "email")
        m = re.search(r"\b(mornings?|afternoons?|evenings?|weekends?|after \d{1,2}(?::\d{2})?\s?(?:am|pm)?|"
                      r"before \d{1,2}(?::\d{2})?\s?(?:am|pm)?)\b(?! deal)", low)
        if m and re.search(r"\b(?:best|catch|reach|call|text|free|available|easier)\b", low):
            add("best_time", m.group(1))
        states = [s for s in STATES if re.search(rf"\b{s}\b", t)]
        for s in states[:3]:
            add("regions", s)
        if re.search(r"\b(?:nationwide|all over|across the country|every state)\b", low):
            add("regions", "nationwide")
        elif re.search(r"\b(?:mostly local|all local|local businesses|in town)\b", low):
            add("regions", "local")
        return {"facts": facts, "summary": _cap((text or "").strip().split("\n")[0])[:160]}

    def extract_call(self, transcript: Any, partner: dict[str, Any], us: list[str],
                     today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        ours = {u.lower() for u in us if u}
        theirs = [s["text"] for s in transcript.segments if s.get("speaker", "").lower() not in ours]
        facts = self.extract_text(" ".join(theirs), partner)["facts"]
        commitments = []
        first = partner.get("first_name") or "them"
        for seg in transcript.segments:
            owner = "us" if seg.get("speaker", "").lower() in ours else "partner"
            for clause in re.split(r"[.!?]\s+|,\s*(?:and|but)\s+(?=(?:i|we)\b)", seg["text"], flags=re.I):
                m = re.search(r"\b(?:i'll|i will|we'll|we will|let me)\s+(send|get|follow up|text|email|put together|"
                              r"share|introduce|set up|book|call)\b([^.!?\n]{0,110})", clause, re.I)
                if not m:
                    continue
                what = _cap(f"{m.group(1)}{m.group(2)}")
                # their promise to us reads "send us the file"; ours to them names them
                what = re.sub(r"\byou\b", "us" if owner == "partner" else first, what, flags=re.I)
                what = re.sub(r"\byour\b", "our" if owner == "partner" else "their", what, flags=re.I)
                if owner == "partner":  # their promise, in our words: "send us a file for one of their clients"
                    what = re.sub(r"\bmy\b", "their", what, flags=re.I)
                    what = re.sub(r"\bme\b", "them", what, flags=re.I)
                commitments.append({"owner": owner, "what": what, "due": due_from(clause, today)})
        learned = sorted({f["slot"].replace("_", " ") for f in facts})
        summary = (f"{round(transcript.duration_min or 0)}-minute call with {partner.get('first_name') or 'the partner'}."
                   + (f" Learned: {', '.join(learned)}." if learned else "")
                   + (f" {len(commitments)} follow-up{'s' if len(commitments) != 1 else ''} agreed." if commitments else ""))
        return {"facts": facts, "commitments": commitments[:8], "summary": summary}


# What each slot means, for the model. Tier and line of work come from the record, and open loops come from
# commitments and reply intents, so the model never fills those.
SLOT_GUIDE = {
    "goals": "what the partner wants to achieve, in their words",
    "client_types": "the kinds of businesses their clients are",
    "needs": "what would help the partner, from us",
    "deal_types": "what their clients need funding for (equipment, working capital, a line of credit...)",
    "deal_size": "the typical amount their clients need",
    "regions": "states or areas their clients are in",
    "channel": "how they prefer we reach them: text, phone call, or email",
    "best_time": "when they are generally easiest to reach (not one appointment)",
    "blockers": "what has kept them from sending deals",
    "products_used": "funding products they have sent deals for",
    "past_issues": "problems they had with us before",
    "tone": "how they like to be talked to",
    "personal": "personal details they volunteered",
    "note": "anything else worth remembering about them",
}
NOT_FROM_MODEL = {"tier", "niche", "open_loop"}
STATE_NAMES = set(STATES)


def tidy(facts: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Put a model's facts into the profile's own terms: one value per fact, deal types and channels in the
    profile's vocabulary, amounts as "around $150k", times of day as "mornings". Drops what doesn't fit its slot."""
    out: list[dict[str, str]] = []

    def keep(slot: str, value: str) -> None:
        value = _cap(value)
        first = value.split(" ", 1)[0]
        if slot in {"client_types", "deal_types", "goals", "needs", "blockers", "products_used"} and first[:1].isupper() \
                and not first.isupper() and first not in STATE_NAMES and not first.startswith("I"):
            value = value[:1].lower() + value[1:]
        if value and len(value) > 2 and {"slot": slot, "value": value} not in out:
            out.append({"slot": slot, "value": value[:120]})

    for f in facts:
        slot = str(f.get("slot") or "")
        whole = str(f.get("value") or "")
        # a single-value slot keeps its first reading ("mornings; on the road most afternoons" is mornings)
        for value in [whole] if slot in {"channel", "best_time", "deal_size", "tone"} else re.split(r"\s*;\s*", whole):
            if not value.strip():
                continue
            if slot == "deal_types":
                labels = [label for pat, label in NEEDS if re.search(pat, value, re.I)]
                for label in labels or [value]:
                    keep(slot, label)
            elif slot == "deal_size":
                keep(slot, _money(value) or (value if len(value) <= 40 else ""))
            elif slot == "channel":
                low = value.lower() if len(value) <= 30 else ""  # a sentence here is something else misfiled
                keep(slot, "text" if re.search(r"\btext|\bsms\b", low) else "phone call" if re.search(r"\bcall|phone", low)
                     else "email" if "email" in low else "")
            elif slot == "best_time":
                m = re.search(r"\b(morning|afternoon|evening|weekend)s?\b", value, re.I)
                keep(slot, m.group(1).lower() + "s" if m else (value if len(value) <= 30 else ""))
            elif slot == "regions":
                states = [st for st in STATES if re.search(rf"\b{st}\b", value)]
                for st in states or ["nationwide" if re.search(r"nationwide|all over|across the country", value, re.I)
                                     else value if len(value) <= 40 else ""]:
                    keep(slot, st)
            else:
                keep(slot, value)
    return out


class ModelExtractor:
    name = "model"
    SYSTEM = ("You keep a funding company's partner profiles. Pull out only what the partner plainly said about "
              "themselves and their business. Never guess. Never record health, religion, politics, account or ID "
              "numbers. Use only these slots, one short value per fact, in the partner's own terms:\n{slots}")

    def __init__(self, slots: list[str], client: llm.LLM | None = None):
        self.slots = [s for s in slots if s not in NOT_FROM_MODEL]
        self.client = client or llm.LLM()
        self.rules = RuleExtractor()
        self.fallbacks: list[str] = []  # times the rules answered because the model failed, and why

    def _system(self) -> str:
        return self.SYSTEM.format(slots="\n".join(f"- {s}: {SLOT_GUIDE.get(s, s.replace('_', ' '))}" for s in self.slots))

    def extract_text(self, text: str, partner: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            data = self.client.chat_json(self._system(),
                                         'Return {"facts": [{"slot": "...", "value": "..."}], "summary": "one line"} '
                                         f"for this message from a partner:\n\n{text}", max_tokens=800, temperature=0)
            facts = tidy([f for f in data.get("facts", []) if isinstance(f, dict) and f.get("slot") in self.slots])
            return {"facts": facts, "summary": str(data.get("summary") or "")[:200]}
        except Exception as exc:  # noqa: BLE001 - the rules are the floor
            self.fallbacks.append(f"text: {exc}")
            return self.rules.extract_text(text, partner)

    def extract_call(self, transcript: Any, partner: dict[str, Any], us: list[str],
                     today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        try:
            data = self.client.chat_json(
                self._system(),
                f"Today is {today.isoformat()}. The partner is {partner.get('name')}; our side is {', '.join(us)}. "
                'Return {"summary": "2-3 sentences", "facts": [{"slot","value"}], "commitments": [{"owner": "us" or '
                '"partner", "what": "...", "due": "YYYY-MM-DD"}]} for this call transcript:\n\n' + transcript.text()[:24000],
                max_tokens=2000, temperature=0)
            facts = tidy([f for f in data.get("facts", []) if isinstance(f, dict) and f.get("slot") in self.slots])
            commitments = [c for c in data.get("commitments", []) if isinstance(c, dict) and c.get("what")]
            for c in commitments:
                c["owner"] = "us" if c.get("owner") == "us" else "partner"
                if not re.match(r"\d{4}-\d{2}-\d{2}$", str(c.get("due") or "")):
                    c["due"] = due_from(str(c.get("what")), today)
            return {"facts": facts, "commitments": commitments[:8], "summary": str(data.get("summary") or "")[:600]}
        except Exception as exc:  # noqa: BLE001
            self.fallbacks.append(f"call: {exc}")
            return self.rules.extract_call(transcript, partner, us, today)


def open_extractor(slots: list[str], use_model: bool | None = None) -> RuleExtractor | ModelExtractor:
    if use_model if use_model is not None else llm.enabled():
        return ModelExtractor(slots)
    return RuleExtractor()
