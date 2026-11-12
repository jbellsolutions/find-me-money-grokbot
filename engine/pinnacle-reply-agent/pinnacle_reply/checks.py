"""The draft checker every reply passes before it goes to a poster.

The rules follow Find Me Money Group's charter (A1, Justin's decisions of 2026-10-31): approval talk, speed claims,
"0% credit lines" and "I've funded" are allowed when true, and no disclosure sentence is required. What stays is
what the law fixes or the charter keeps for every reply:

- no guarantee or promise of approval before a lender decides (the FTC Act, Florida's FDUTPA);
- no fees up front;
- never ask for or repeat an SSN, date of birth, bank login or account number;
- no earnings or income claims;
- never pose as a customer or write a testimonial (the FTC's 2024 rule on fake reviews);
- no link and no push to DM, message, call, text or email us;
- no rate quote other than 0%;
- exactly one question, at most 90 words.

Contact details depend on the kind of message (spec 36 section 7). A FIRST reply asks for nothing: no email, no phone
number, no permission to be contacted. A FOLLOW-UP (a reply after they answered us) may ask, once, for the best email
or number and their OK for a funding partner to reach them; that ask is the follow-up's one question. Pushing people
toward us ("call me", "my number", "DM me") stays blocked in both kinds.

`g3_violations` is the shared part (guardrail G3) the creators lane's own drafts are judged by. Lead Radar's
`draft_violations` and the creators lane still run the older, stricter G3 until they're updated, so a draft they
write passes here, while a draft written here can carry words (approved, qualified) they would still refuse.
"""

from __future__ import annotations

import re

# Optional (charter sections 3 and 5): a draft may carry it once. Nothing requires it.
BRAND_LINE = "I'm with Find Me Money Group."

_A = "['’]"  # a straight or a curly apostrophe
G3_RULES = [
    ("guaranteed", re.compile(r"\bguarantee(?:d|s)?\b", re.I), False),
    ("approval promise", re.compile(
        rf"\b(?:you{_A}?ll|you will|you{_A}?re going to)\s+(?:definitely\s+|surely\s+|certainly\s+)?(?:be|get)\s+"
        rf"(?:approved|funded)\b|\b(?:we{_A}?ll|we will|I{_A}ll|I will)\s+(?:definitely\s+|surely\s+)?get you\s+"
        rf"(?:approved|funded)\b|\bcan{_A}?t be (?:denied|declined|turned down)\b|\beveryone (?:gets|is) approved\b",
        re.I), True),
    ("DM", re.compile(r"\bDMs?\b|\bdm me\b|\bPM me\b|direct message|message me|inbox me|send me a message|shoot me a message",
                      re.I), False),
    ("sensitive data", re.compile(r"\bSSN\b|social security|date of birth|\bDOB\b|bank account (?:number|#|info)|"
                                  r"routing number|account number|"
                                  r"\bbank (?:log-?ins?|sign-?ins?|passwords?|credentials)\b|"
                                  r"online banking (?:log-?ins?|passwords?|credentials)|\b\d{3}-\d{2}-\d{4}\b",
                                  re.I), False),
    ("upfront fee", re.compile(r"\bup[- ]?front (?:fee|cost|payment)s?|\bfees? (?:up[- ]?front|in advance)\b|"
                               r"application fee|processing fee", re.I), True),
    ("link", re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(?:com|net|org|io|co)\b", re.I), False),
    ("earnings claim", re.compile(r"\b(?:makes?|making|earns?|earning|brings? in|nets?|clears?|generates?)\s+"
                                  r"(?:about |around |up to |over |at least )?\$\s?\d|passive income|"
                                  r"\b(?:six|seven)[- ]figure (?:income|salary|business)\b|"
                                  r"\bpays? for (?:itself|themselves)\b", re.I), False),
]
# "0%" is allowed ("0% credit lines"). Any other number before a percent sign or the word "percent", and any APR, is
# a rate quote. The lookbehind keeps the 0 in "10%", "100%" or "30%" from passing as "0%".
RATE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s?(?:%|percent\b)|\bAPR\b|\bpercent\b", re.I)
PERSONA_RULES = [
    # "I've funded" and "our network has funded" are fine (charter section 3); posing as a customer is not.
    ("vouching", re.compile(r"\bworked (?:great |well )?for me\b|\bI got (?:funded|a loan|approved)\b|\bhighly recommend\b|"
                            r"\bthey (?:helped|funded|approved) me\b", re.I), False),
    ("contact push", re.compile(r"\b(?:call|text|email) me\b|\breach out to me\b|\bmy (?:number|email|cell)\b|"
                                r"\blink in (?:my )?bio\b|\bcheck (?:out )?my (?:page|profile)\b", re.I), False),
]
# Asking THEM for details or their OK. Not allowed in a first reply; allowed once in a follow-up. "your number" doesn't
# catch "your number of employees" or "your numbers".
_TO_YOU = r"(?:reach(?:es|ed)?(?:\s+out)?|contact(?:s|ed)?|call(?:s|ed)?|text(?:s|ed)?|e-?mail(?:s|ed)?)\s+(?:out\s+to\s+)?you"
CONTACT_ASK = re.compile(
    r"\byour\s+(?:best\s+|preferred\s+)?(?:e-?mail|phone|cell|mobile)\b|\byour\s+(?:best\s+)?(?:phone\s+)?number\b(?!\s+of)|"
    r"\b(?:best|good|preferred)\s+(?:e-?mail|number|phone|way to (?:reach|contact)|time to call)\b|"
    rf"\b(?:ok(?:ay)?|alright|fine|comfortable|mind|permission)\b[^.?!]{{0,70}}\b{_TO_YOU}\b|"
    rf"\b(?:can|could|may|would)\s+(?:a|an|the|our|my|one of|someone|somebody|we|I)\b[^.?!]{{0,50}}\b{_TO_YOU}\b", re.I)
FIRST, FOLLOW_UP = "first", "follow_up"
NEGATION = re.compile(rf"\b(?:no|never|zero|without|don{_A}t|do not|won{_A}t|aren{_A}t|not|can{_A}t|cannot)\b"
                      r"[^.?!]{0,25}$", re.I)
MAX_WORDS = 90


def _matches(rules, text: str) -> list[str]:
    out = []
    for name, rx, negatable in rules:
        for m in rx.finditer(text):
            if negatable and NEGATION.search(text[: m.start()]):
                continue
            out.append(name)
            break
    return out


def _rate_quote(text: str) -> bool:
    for m in RATE.finditer(text):
        number = m.group(1)
        if number is not None and float(number) == 0:
            continue  # "0%", "0 percent"
        if number is None and m.group(0).lower() == "percent" and re.search(r"\bzero\s$", text[: m.start()], re.I):
            continue  # "zero percent"
        return True
    return False


def g3_violations(text: str | None) -> list[str]:
    """Guardrail G3: the shared rules, plus a qualifying question and the length limit."""
    text = text or ""
    out = _matches(G3_RULES, text)
    if "?" not in text:
        out.append("no qualifying question")
    if not text.strip():
        out.append("empty")
    elif len(text.split()) > MAX_WORDS:
        out.append("too long")
    return out


def asks_contact(text: str | None) -> bool:
    """Whether a reply asks for their details or their OK to be contacted."""
    return bool(CONTACT_ASK.search(text or ""))


def violations(text: str | None, kind: str = FIRST, may_ask: bool = True) -> list[str]:
    """Every rule a persona reply breaks: G3, then no rate quote (0% is fine), no vouching, no contact push and
    exactly one question. `kind` is FIRST (the default) or FOLLOW_UP. A first reply may not ask for contact details; a
    follow-up may, unless `may_ask` is False (it already asked, already has them, or REPLY_GHL is off): then it may not."""
    text = text or ""
    out = g3_violations(text)
    if _rate_quote(text):
        out.append("rate quote")
    out += _matches(PERSONA_RULES, text)
    if text.count("?") > 1:
        out.append("more than one question")
    if asks_contact(text):
        if kind != FOLLOW_UP:
            out.append("contact ask in a first reply")
        elif not may_ask:
            out.append("contact ask not allowed now")
    return out


def passes(text: str | None, kind: str = FIRST, may_ask: bool = True) -> bool:
    return not violations(text, kind, may_ask)
