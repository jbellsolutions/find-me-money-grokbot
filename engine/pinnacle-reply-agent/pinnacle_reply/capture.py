"""What a lead tells us in an answer, pulled out before anything is scrubbed (spec 36 sections 2 and 7).

An answer can carry an email, a phone number and an OK for a funding partner to reach them. The ledger, the vault, the
notes and the logs never hold them (G5: `ledger.scrub` takes them out of every text kept), so this runs first, on the
raw words, and hands the details to the GHL contact through the outbox (`ledger.take_contact`, `ghl` op
`contact_details`). This module only reads text: it stores and sends nothing.

`partner_ok` is strict on purpose. A missed yes costs one nudge; a false yes would put "consent" on someone who never
gave it. It wants an explicit invitation to be contacted, in a sentence with no question mark, no hedge and no
negation, and nothing anywhere in the message that opts out.
"""

from __future__ import annotations

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)")


def phone_e164(match: str) -> str:
    """+1XXXXXXXXXX for a plausible US number, else "" (a long number that isn't a phone, like 1000000000)."""
    digits = re.sub(r"\D", "", match)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] in "01" or digits[3] in "01":
        return ""
    return "+1" + digits


def extract(text: str | None) -> dict[str, str]:
    """{"email", "phone"}: the first of each in the text, normalised, "" when there is none."""
    text = text or ""
    email = EMAIL.search(text)
    phone = next((p for p in (phone_e164(m.group(0)) for m in PHONE.finditer(text)) if p), "")
    return {"email": email.group(0).lower() if email else "", "phone": phone}


_VERB = r"(?:call|contact|reach|e-?mail|text|phone|ring|message)"
_ME = r"(?:me|us)"
# Who may be doing the contacting: the funding partner, or "you" (us). Never a bank, a lender, a CPA.
_SOMEONE = r"(?:them|a partner|your partner|the partner|a funding partner|the funding partner|someone|somebody)"
_DOER = rf"(?:{_SOMEONE}|you|your team|one of (?:them|your [\w ]{{1,15}}?))"
_YES = (r"(?:yes|yeah|yep|yup|sure|ok|okay|absolutely|definitely|please|go ahead|sounds good|that works|fine by me|"
        r"i'?m (?:ok|okay|fine|good|happy)|i am (?:ok|okay|fine|good|happy)|happy to|i consent|i agree)")
INVITES = [
    # "yes have them call me", "let a partner reach out to me": the object must be me/us
    re.compile(rf"\b(?:have|let|get|ask)\s+{_SOMEONE}\s+(?:to\s+)?{_VERB}(?:\s+out)?(?:\s+to)?\s+{_ME}\b", re.I),
    # "feel free to call me", "you can email me", "please contact me", "go ahead and text me"
    re.compile(rf"\b(?:feel free to|you (?:can|may|could)|please|go ahead and|go ahead to|welcome to)\s+{_VERB}(?:\s+out)?"
               rf"(?:\s+to)?\s+{_ME}\b", re.I),
    # "ok with them calling me", "sure, a partner reaching me is fine": the doer sits right before the verb
    re.compile(rf"\b{_YES}\b[^.?!]{{0,30}}?\b{_DOER}\s+(?:to\s+)?{_VERB}(?:ing|s)?(?:\s+out)?(?:\s+to)?\s+{_ME}\b", re.I),
]
# Anything that hedges, asks, refuses, conditions or looks ahead. A sentence with one of these is never a yes.
HEDGE = re.compile(r"\b(?:no|not|never|don['’]?t|do not|won['’]?t|can['’]?t|cannot|stop|unsubscribe|remove|without|except|"
                   r"unless|if|maybe|perhaps|might|probably|possibly|depends|unsure|guess|think|wish|rather|instead|"
                   r"prefer|later|someday|eventually|only|but|however|though|although|sometime|once|"
                   r"will|would|gonna|going to)\b|\bi['’]?(?:ll|d)\b|\bwe['’]?ll\b|n['’]t\b", re.I)
OPT_OUT = re.compile(r"\b(?:do not|don['’]?t|stop|never|unsubscribe|leave me alone|not interested|no thanks|remove me)\b",
                     re.I)


def partner_ok(text: str | None) -> bool:
    """Whether the answer clearly says yes to being contacted. False on "maybe", a question, a "don't", a bare "yes"."""
    text = (text or "")[:2000]
    if not text.strip() or OPT_OUT.search(text):
        return False
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if not sentence.strip() or "?" in sentence or HEDGE.search(sentence):
            continue
        if any(rx.search(sentence) for rx in INVITES):
            return True
    return False
