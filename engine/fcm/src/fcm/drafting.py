"""Drafts in the partner manager's voice: the kickoff text, conversation replies, and the revenue plan.

Two drafters share one interface:
  * TemplateDrafter  the framework in knowledge/funding/07-kickoff-framework.md, as code. Deterministic:
                     the simulation, the tests, and the floor when no model is configured.
  * ModelDrafter     the drafting model (fcm.llm) working inside the same framework. Every model draft is
                     checked (length, one question, names, no AI talk, no claims) and replaced by the
                     template when it fails.

Messages are always signed by the partner's named manager. They never mention AI, drafting or an
assistant, and never claim anything about who is typing: identity questions go to the manager.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any

from . import cadence, llm

STOP_SUFFIX = " Reply STOP to opt out."
VARIANTS = {
    "A": ("Hey {first}, it's {sender} with {company}. {hook}, and I'm now your partner manager. I'd love to learn "
          "what you're working toward and how we can help you close more deals. Open to a quick call this week?"),
    "B": ("Hi {first}, {sender} here from {company}. {hook}, and I just became your partner manager. I'm reaching "
          "out personally to learn your goals and see where we can help. Got time for a quick call this week?"),
    "C": ("Hey {first}! It's {sender} at {company}. {hook}, and I'm your new partner manager. I want to get to "
          "know your business and how we can help you close more deals. Would a quick call this week work?"),
}
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
NUDGE = ("Hey {first}, {sender} again from {company}. No rush at all, I just didn't want my last text to get "
         "buried. Is there a better time to connect?")
SOURCE_PHRASES = {"skool": "our Skool community", "linkedin": "LinkedIn", "referral": "a referral",
                  "webinar": "one of our webinars", "event": "one of our events", "facebook": "Facebook",
                  "website": "our website"}
# Things a partner text must never say. The engine's lint enforces the same list at prepare time.
NEVER_SAY = re.compile(r"\bAI\b|artificial intelligence|chat ?bot|\bbot\b|automated|language model|assistant|"
                       r"drafted|real person|i'?m (?:a )?human|i am (?:a )?human|haven'?t heard from you|"
                       r"been a while|inactive|went quiet|gone quiet|\$\s?\d|guarantee", re.I)
PRODUCTS = {
    "equipment financing": ["Business Term Loan", "Short-Term Business Loan"],
    "working capital": ["Short-Term Business Loan", "Business Line of Credit"],
    "inventory financing": ["Business Line of Credit"],
    "a line of credit": ["Business Line of Credit"],
    "SBA loans": ["SBA Loan"],
    "expansion capital": ["SBA Loan", "Business Term Loan"],
    "business credit cards": ["0% intro-rate business credit cards"],
    "startup funding": ["0% intro-rate business credit cards", "Business-Purpose Personal Term Loan"],
    "short-term funding": ["Short-Term Business Loan"],
}
GROWTH_SERVICES = {"a funnel page": "a funnel page for their funding referrals", "lead reactivation":
                   "reactivating their own old leads", "social content": "social content", "email campaigns":
                   "an email campaign to their list", "CRM help": "CRM help", "more leads": "a lead-gen plan"}
# A question asking for a call: the kickoff's last line, our call ask, or a model's rewording of either.
CALL_ASK = re.compile(r"\b(?:quick|short|15-minute|hop on a|jump on a|set up a|grab a)\b[^?]*\bcall\b[^?]*\?|"
                      r"\bcall\b[^?]*\b(?:this|next) week\b[^?]*\?", re.I)
OUR_MESSAGES = {"kickoff_sent", "nudge_sent", "message_sent"}


def segments(body: str) -> int:
    return cadence.sms_segments(cadence.sms_normalize(body) + STOP_SUFFIX)["segments"]


def variant_for(contact_id: str, variants: list[str]) -> str:
    variants = [v for v in variants if v in VARIANTS] or ["A"]
    return variants[int(hashlib.sha256(contact_id.encode()).hexdigest(), 16) % len(variants)]


def hooks(p: dict[str, Any]) -> list[dict[str, str]]:
    """One personal line from their record, most reliable first: deals, tier, tenure, niche, source."""
    year = (p.get("joined") or "")[:4]
    out = []
    if p.get("deals"):
        n = p["deals"]
        out.append({"kind": "deals", "text": f"You've sent us {n} deal{'s' if n != 1 else ''}"
                                             + (f" since {year}" if year else "")})
    if p.get("tier") and p["tier"] != "Bronze":
        out.append({"kind": "tier", "text": f"You're one of our {p['tier']} partners"})
    if year:
        out.append({"kind": "tenure", "text": f"You've been a partner with us since {year}"})
    if p.get("niche"):
        niche = p["niche"]
        out.append({"kind": "niche", "text": f"You've been with us as {'an' if niche[:1].lower() in 'aeiou' else 'a'}"
                                             f" {niche}"})
    if p.get("source") in SOURCE_PHRASES:
        out.append({"kind": "source", "text": f"You joined us through {SOURCE_PHRASES[p['source']]}"})
    out.append({"kind": "fallback", "text": "You joined our partner program a while back"})
    return out


def _month(day: str) -> str:
    """'2025-03-14' -> 'March 2025'; '' when it isn't a date."""
    m = re.match(r"(\d{4})-(\d\d)", day or "")
    return f"{MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m and 1 <= int(m.group(2)) <= 12 else ""


def liaison_hooks(p: dict[str, Any]) -> list[dict[str, str]]:
    """Variant L's line from the partner file, most telling first: their last deal, their deal count, when they
    joined, what they do. Never how long they've been quiet (NEVER_SAY)."""
    out = []
    if last := _month(p.get("last_deal", "")):
        out.append({"kind": "last_deal", "text": f"I see the last deal you sent us was back in {last}"})
    if p.get("deals"):
        n = p["deals"]
        out.append({"kind": "deals", "text": f"I see you've sent us {n} deal{'s' if n != 1 else ''} so far"})
    if joined := _month(p.get("joined", "")):
        out.append({"kind": "joined", "text": f"I see you joined our partner program in {joined}"})
    if p.get("niche"):
        niche = p["niche"]
        out.append({"kind": "niche", "text": f"I see you work with us as {'an' if niche[:1].lower() in 'aeiou' else 'a'}"
                                             f" {niche}"})
    out.append({"kind": "fallback", "text": "Your name is on my list of partners to get to know"})
    return out





def check(body: str, p: dict[str, Any], sender: str, *, kickoff: bool = False, max_segments: int = 2) -> list[str]:
    """Problems with a draft. Empty means it can go to the manager for review."""
    problems = []
    if NEVER_SAY.search(body):
        problems.append(f"says something partner texts never say: {NEVER_SAY.search(body).group(0)!r}")
    if body.count("?") > 1:
        problems.append("more than one question")
    if kickoff:
        if body.count("?") != 1:
            problems.append("a kickoff asks exactly one question")
        if p.get("first_name") and p["first_name"] not in body:
            problems.append("missing their first name")
        if sender not in body:
            problems.append("not signed by the manager")
        if segments(body) > max_segments:
            problems.append(f"longer than {max_segments} SMS segments")
    elif segments(body) > 3:
        problems.append("too long for a text")
    return problems


class TemplateDrafter:
    name = "template"

    kind = "a business-funding company"  # what the company is, for the model's voice (kickoff.json company_kind)

    def __init__(self, company: str = "Find Me Money Group", calendar_link: str = "", max_segments: int = 2):
        self.company = company
        self.calendar_link = calendar_link
        self.max_segments = max_segments

    def kickoff(self, p: dict[str, Any], sender: str, variant: str) -> dict[str, Any]:
        template = VARIANTS.get(variant, VARIANTS["A"])
        first = p.get("first_name") or "there"
        lines = liaison_hooks if variant == "L" else hooks
        for hook in lines(p):
            body = template.format(first=first, sender=sender, company=self.company, hook=hook["text"])
            if segments(body) <= self.max_segments:
                return {"body": body, "hook": hook["kind"], "variant": variant, "drafter": self.name}
        body = template.format(first=first, sender=sender, company=self.company, hook=lines({})[-1]["text"])
        return {"body": body, "hook": "fallback", "variant": variant, "drafter": self.name}

    def nudge(self, p: dict[str, Any], sender: str) -> str:
        return NUDGE.format(first=p.get("first_name") or "there", sender=sender, company=self.company)

    def next_move(self, p: dict[str, Any], intent: str, inbound: str) -> dict[str, str]:
        """What our reply should do: confirm a time they offered, book the call, ask the next discovery question,
        or just acknowledge. The model drafter rewords these moves; it never picks a different one."""
        history = p.get("history", [])  # newest first
        ours = [i for i in history if i["kind"] in OUR_MESSAGES]
        asked_call = bool(ours) and bool(CALL_ASK.search(ours[0].get("summary") or ""))
        asks = sum(1 for i in ours if CALL_ASK.search(i.get("summary") or ""))
        talked = any(i["kind"] == "call" for i in history)
        signals = cadence.reply_signals(inbound)
        texter = signals["prefers_text"] or "text" in [v.lower() for v in p.get("values", {}).get("channel", [])]
        if intent in cadence.NO_DRAFT_INTENTS:
            return {"move": intent}
        if intent == "has_deal":  # a deal outranks everything, even a "perfect timing" that sounds like a yes
            return {"move": "has_deal"}
        if intent == "will_send_deals":
            return {"move": "ask_for_deal"}
        if intent == "book_call" or (asked_call and signals["affirmative"] and intent in {"general_reply", "question"}):
            if signals["proposed_time"]:
                return {"move": "confirm_time", "time": signals["proposed_time"]}
            return {"move": "book"}
        if intent == "not_interested":
            return {"move": "close_out"}
        if intent in {"question", "commission_question", "check_back_later", "event_interest"}:
            return {"move": intent}
        can_ask_call = not talked and not texter and not asked_call and asks < 2
        if intent == "wants_service" and can_ask_call:
            return {"move": "call_ask", "why": "scope the help they asked for"}
        replies = sum(1 for i in history if i["kind"] == "reply")
        # the kickoff already asked once; ask again after two replies, never twice in a row, never to a texter
        if replies >= 2 and can_ask_call:
            return {"move": "call_ask"}
        recent = " ".join((i.get("summary") or "") for i in ours[:2]).lower()
        for q in p.get("open_questions") or ([p["next_question"]] if p.get("next_question") else []):
            if q["question"].lower() not in recent:  # don't ask again what we asked in our last two texts
                return {"move": "discover", "slot": q["slot"], "question": q["question"]}
        return {"move": "call_ask" if can_ask_call else "acknowledge"}

    def _opener(self, p: dict[str, Any], first: str, options: tuple[str, ...]) -> str:
        """A different opening line from our last message, so a thread never reads like a form letter."""
        ours = [i for i in p.get("history", []) if i["kind"] in OUR_MESSAGES]
        last = (ours[0].get("summary") or "").lower() if ours else ""
        n = len(ours)
        for k in range(len(options)):
            line = options[(n + k) % len(options)].format(first=first)
            if line.split(",")[0].lower() not in last:
                return line
        return options[n % len(options)].format(first=first)

    def reply(self, p: dict[str, Any], sender: str, intent: str, inbound: str,
              follow_up_date: str = "") -> dict[str, Any]:
        first = p.get("first_name") or "there"
        move = self.next_move(p, intent, inbound)
        m = move["move"]
        if m in cadence.NO_DRAFT_INTENTS:
            return {"body": "", "move": m, "drafter": self.name}
        if m == "has_deal":  # never ask for a client's file by text: the call collects it
            body = f"That's great, {first}. I'll give you a call today to get the details."
        elif m == "ask_for_deal":
            body = f"Love that, {first}. Do you have one in the pipeline right now that I can help you with?"
        elif m == "close_out":
            body = f"Understood, {first}. Thanks for letting me know. If anything changes, I'm here."
        elif m == "check_back_later":
            when = f" around {follow_up_date}" if follow_up_date else " then"
            body = f"Totally understand, {first}. I'll reach back out{when}. Good luck in the meantime!"
        elif m in {"question", "commission_question"}:
            body = f"Good question, {first}. Let me get you the exact answer today."
        elif m == "event_interest":
            body = f"Will do, {first}! I'll send the link over so you can grab a spot."
        elif m == "confirm_time":
            when = move["time"][:1].upper() + move["time"][1:]
            body = f"{when} works, {first}. I'll give you a call then. Talk soon!"
        elif m == "book":
            body = (f"Perfect. Grab any time that works for you here: {self.calendar_link}" if self.calendar_link
                    else f"Perfect, {first}. What day and time work best for you?")
        elif m == "call_ask":
            lead = (f"Happy to help with that, {first}." if move.get("why")
                    else self._opener(p, first, ("Really appreciate you sharing that, {first}.", "Thanks, {first}.",
                                                 "Good to know, {first}.")))
            body = f"{lead} Would a quick 15-minute call this week be easier to talk it through?"
        elif m == "discover":
            lead = self._opener(p, first, ("Great to hear from you, {first}!", "Thanks for sharing that, {first}.",
                                           "Got it, {first}.", "Appreciate that, {first}."))
            body = f"{lead} {move['question']}"
        else:
            body = self._opener(p, first, ("Thanks, {first}. Really glad we connected.",
                                           "Appreciate it, {first}. Talk soon.", "Sounds good, {first}. Thank you!"))
        return {"body": body, "move": m, "drafter": self.name}

    def revenue_plan(self, p: dict[str, Any]) -> str:
        v = p.get("values", {})
        first = p.get("first_name") or "them"
        needs = v.get("deal_types", [])
        products: list[str] = []
        for need in needs:
            for prod in PRODUCTS.get(need, []):
                if prod not in products:
                    products.append(prod)
        who = ", ".join(v.get("client_types", [])[-2:]) or (p.get("niche") or "their clients")
        regions = ", ".join(v.get("regions", [])[-3:])
        lines = [f"**Who they serve:** {who}" + (f" ({regions})" if regions else ""),
                 f"**What their clients need:** {', '.join(needs[-3:]) or 'not known yet'}"
                 + (f", {v['deal_size'][-1]}" if v.get("deal_size") else ""),
                 f"**Programs to lead with:** {', '.join(products[:3]) or 'ask on the next call'}"]
        if v.get("goals"):
            lines.append(f"**Their goal:** {v['goals'][-1]}")
        steps = [loop["text"] for loop in p.get("open_loops", [])][:2]
        services = [GROWTH_SERVICES[n] for n in v.get("needs", []) if n in GROWTH_SERVICES]
        if services:
            steps.append(f"Offer {services[0]} (growth service)")
        if not any("submission link" in s for s in steps):
            steps.append("Send the deal-submission link with a short note on the programs above")
        if p.get("next_question"):
            steps.append(f"Next check-in, ask: \"{p['next_question']['question']}\"")
        lines.append("**Next 30 days:**")
        lines += [f"{i}. {s}" for i, s in enumerate(steps[:4], 1)]
        lines.append(f"**How we'll know it's working:** deals submitted by {first}, counted by month.")
        return "\n".join(lines)


class ModelDrafter(TemplateDrafter):
    name = "model"
    VOICE = ("You write text messages for {sender}, a partner manager at {company}, {kind}. "
             "{sender} is writing to one of the company's referral partners. Warm, plain, peer-to-peer, short. "
             "Never mention AI, assistants, drafting or automation, and never say anything about who is typing. "
             "Never promise approvals, rates, amounts or income, and never write a dollar figure, even one they said. "
             "Never guilt them about being quiet, and never imply a past conversation that didn't happen. Exactly one "
             "question unless told otherwise.")

    def _draft(self, sender: str, prompt: str, ok: Any, max_tokens: int) -> tuple[str, list[str]]:
        """Ask once; if the draft breaks a rule, say which and ask once more. Returns (text, problems)."""
        system = self.VOICE.format(sender=sender, company=self.company, kind=self.kind)
        text, problems = "", ["no draft"]
        for _ in range(2):
            text = self.client.chat(system, prompt, max_tokens=max_tokens, temperature=0.5).strip().strip('"')
            problems = ok(text)
            if not problems:
                break
            prompt += f"\n\nYour draft was:\n{text}\n\nIt broke these rules: {'; '.join(problems)}. Write it again."
        return text, problems

    def __init__(self, company: str = "Find Me Money Group", calendar_link: str = "", max_segments: int = 2,
                 client: llm.LLM | None = None):
        super().__init__(company, calendar_link, max_segments)
        self.client = client or llm.LLM()
        self.fallbacks: list[str] = []  # drafts where the template stood in for the model, and why

    def _context(self, p: dict[str, Any]) -> str:
        facts = "; ".join(f"{k}: {', '.join(v[-2:])}" for k, v in p.get("values", {}).items() if v)
        recent = " | ".join(f"{i['at']} {i['kind']}: {i.get('summary', '')[:140]}" for i in p.get("history", [])[:6])
        return (f"Partner: {p.get('name')} (first name {p.get('first_name')}). Tier: {p.get('tier') or 'unknown'}. "
                f"Joined: {p.get('joined') or 'unknown'}. Deals sent: {p.get('deals', 0)}. Profile: {p.get('summary')} "
                f"Known facts: {facts or 'none'}. Recent: {recent or 'none'}.")

    def kickoff(self, p: dict[str, Any], sender: str, variant: str) -> dict[str, Any]:
        base = super().kickoff(p, sender, variant)
        try:
            text, problems = self._draft(
                sender, f"{self._context(p)}\n\nThis is {sender}'s first text to them. Start from this approved text and "
                f"keep its structure, greeting, signature, its personal detail (chosen from their record on purpose) "
                f"and its closing question:\n\n{base['body']}\n\nSmooth the wording so it sounds like {sender} "
                "wrote it to this one person. Add no new facts. Keep it under 280 characters. Return only the text.",
                lambda t: check(t, p, sender, kickoff=True, max_segments=self.max_segments), 220)
            if not problems:
                return {**base, "body": text, "drafter": self.name}
            self.fallbacks.append(f"kickoff: {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001 - the template is the floor
            self.fallbacks.append(f"kickoff: {exc}")
        return base

    def reply(self, p: dict[str, Any], sender: str, intent: str, inbound: str,
              follow_up_date: str = "") -> dict[str, Any]:
        base = super().reply(p, sender, intent, inbound, follow_up_date)
        if not base["body"]:
            return base
        move = self.next_move(p, intent, inbound)
        warm = ("react to one thing they said in a few natural words, the way a friend would (don't list back what "
                "they told you or call it context)")
        goal = {"discover": f"{warm}, then ask: {move.get('question', '')}",
                "confirm_time": f"confirm you'll call them {move.get('time', '')}; no question needed",
                "ask_for_deal": f"{warm}, then ask if they have a deal in the pipeline now you can help with",
                "call_ask": f"{warm}, then ask if a quick 15-minute call this week works",
                "book": (f"say great and share the booking link {self.calendar_link}; no question needed" if self.calendar_link
                         else "say great and ask what day and time work best")}.get(move["move"], f"reply like this: {base['body']}")
        try:
            text, problems = self._draft(
                sender, f"{self._context(p)}\n\nTheir message: \"{inbound}\"\n\nWrite {sender}'s reply. Goal: {goal}. "
                "Under 300 characters. Return only the text.", lambda t: check(t, p, sender), 200)
            if not problems:
                return {**base, "body": text, "drafter": self.name}
            self.fallbacks.append(f"reply ({move['move']}): {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001
            self.fallbacks.append(f"reply ({move['move']}): {exc}")
        return base

    def revenue_plan(self, p: dict[str, Any]) -> str:
        base = super().revenue_plan(p)
        try:
            text = self.client.chat(
                f"You write short, practical revenue plans for the referral partners of {self.company}, {self.kind}. Use "
                "only the facts given. Never promise approvals, rates or income. Markdown, under 14 lines.",
                f"{self._context(p)}\n\nOpen loops: {[l['text'] for l in p.get('open_loops', [])]}\n\nProducts the "
                f"company offers that fit what their clients need: {sorted({x for n in p.get('values', {}).get('deal_types', []) for x in PRODUCTS.get(n, [])})}\n\n"
                f"Rewrite this plan so it reads well and stays this specific. Keep the same bold headings:\n\n{base}",
                max_tokens=600, temperature=0.3).strip()
            if text and not re.search(r"guarantee|\bAI\b|approval rate", text, re.I) and len(text) < 2000:
                return text
            self.fallbacks.append("revenue plan: empty, too long, or a banned phrase")
        except Exception as exc:  # noqa: BLE001
            self.fallbacks.append(f"revenue plan: {exc}")
        return base


def open_drafter(kickoff_cfg: dict[str, Any], use_model: bool | None = None) -> TemplateDrafter:
    args = (kickoff_cfg.get("sms_company") or kickoff_cfg.get("company", "Find Me Money Group"), kickoff_cfg.get("calendar_link", ""),
            int(kickoff_cfg.get("max_segments", 2)))
    drafter = ModelDrafter(*args) if (use_model if use_model is not None else llm.enabled()) else TemplateDrafter(*args)
    drafter.kind = kickoff_cfg.get("company_kind") or TemplateDrafter.kind
    return drafter
