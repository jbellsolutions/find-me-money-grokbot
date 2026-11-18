#!/usr/bin/env python3
"""Offline SpeakerAgent query/scoring/structural checks. No network or credentials."""
import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

VERSION = "speakeragent-portable-1"
EVENT_TERMS = ["conference", "convention", "summit", "symposium", "congress",
               "forum", "annual meeting", "workshop", "expo"]


def number(value, name, maximum=10):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError(f"{name} must be between 0 and {maximum}")
    return value


def triage(score):
    return "GREEN" if score >= 65 else "YELLOW" if score >= 35 else "RED"


def score_podcast(values):
    topic, recency, reach, guest = [number(values[k], k) for k in
        ("topic_alignment", "recency", "podcast_reach", "guest_format")]
    confidence = number(values["best_topic_confidence"], "best_topic_confidence", 1)
    if confidence < .5:
        adjusted = min(topic, 5)
    elif confidence < .8:
        adjusted = round(min(topic, 5 + ((confidence - .5) / .3) * (topic - 5)))
    else:
        adjusted = topic
    score = max(0, min(100, round((adjusted * .70 + recency * .15 + reach * .10 + guest * .05) * 10)))
    return {"algorithm": "podcast-model-path-v061", "match_score": score,
            "triage": triage(score), "adjusted_topic": adjusted,
            "best_topic_confidence": confidence, "inputs": values,
            "note": "Score only; eligibility and factual evidence require review."}


def score_conference(values):
    weights = {"topic_relevance": .25, "org_type": .20, "audience_size": .10,
               "budget_signals": .10, "geographic_match": .20, "timing_fit": .15}
    score = max(0, min(100, round(sum(number(values[k], k) * w for k, w in weights.items()) * 10)))
    return {"algorithm": "conference-legacy-six-factor", "match_score": score,
            "triage": triage(score), "inputs": values,
            "note": "Historical scorer; not Conference Alpha's relevance gate or verified payment."}


def queries(keywords, geography, as_of):
    cleaned = [k.strip() for k in keywords if k and k.strip()][:8] or ["conference"]
    year = date.fromisoformat(as_of).year
    suffix = f" {geography.strip()}" if geography.strip() else ""
    output = []
    for i, keyword in enumerate(cleaned):
        first, second = EVENT_TERMS[i * 2 % len(EVENT_TERMS)], EVENT_TERMS[(i * 2 + 1) % len(EVENT_TERMS)]
        output.extend([
            f'{keyword} "call for speakers" {first}{suffix} {year}',
            f'{keyword} "call for speakers" {second}{suffix} {year + 1}',
            f'{keyword} {first} "call for proposals"{suffix} {year}',
            f'{keyword} {second} "call for papers"{suffix} {year}',
            f'{keyword} {first} "speaker applications" open{suffix}',
        ])
    return list(dict.fromkeys(output))


def canonical_url(value):
    parts = urlsplit(value)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Expected an HTTP(S) source URL without embedded credentials")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", urlencode(query), ""))


def identity(case):
    # Agent-layer identity: preserves editions and different events on an organizer domain.
    fields = [case.get(k, "") or "" for k in ("client_id", "persona_id", "kind", "name", "edition", "event_date")]
    fields.append(canonical_url(case["official_url"]))
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def validate(case, paid_only=False, minimum_fee=None, currency=None):
    errors = []
    if not isinstance(case, dict):
        return ["case must be an object"]
    for field in ("schema_version", "case_id", "client_id", "persona_id", "kind", "name", "official_url", "observed_at"):
        if not case.get(field):
            errors.append(f"missing {field}")
    if case.get("kind") not in {"conference", "podcast"}:
        errors.append("kind must be conference or podcast")
    for field in ("fit", "eligibility", "compensation", "route", "draft", "research"):
        if not isinstance(case.get(field), dict):
            errors.append(f"{field} must be an object")
    if errors:
        return errors
    try:
        canonical_url(case["official_url"])
        date.fromisoformat(case["observed_at"][:10])
    except (ValueError, TypeError):
        errors.append("invalid official URL or observation date")
    sources = case.get("sources", [])
    if not isinstance(sources, list) or not all(isinstance(s, dict) for s in sources):
        return errors + ["sources must be a list of objects"]
    ids = {s.get("id") for s in sources if s.get("id")}
    if len(ids) != len(sources):
        errors.append("source IDs must be present and unique")
    checked = {s.get("id") for s in sources if s.get("checked") is True and (s.get("excerpt") or s.get("summary"))}
    public_checked = {s.get("id") for s in sources if s.get("id") in checked and s.get("kind", "public") == "public"}
    for source in sources:
        try:
            if source.get("kind") == "client_supplied":
                path = Path(source.get("path", ""))
                if not source.get("path") or path.is_absolute() or ".." in path.parts or not source.get("attribution"):
                    raise ValueError("Client evidence needs a relative path and attribution")
            elif source.get("kind", "public") == "public":
                canonical_url(source.get("url", ""))
            else:
                raise ValueError("Unknown source kind")
            date.fromisoformat(str(source.get("observed_at", ""))[:10])
        except ValueError:
            errors.append(f"source {source.get('id')} needs a valid public URL or attributed client evidence path, and observation date")
    for field in ("fit", "eligibility", "compensation", "route"):
        refs = case[field].get("source_ids", [])
        if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
            errors.append(f"{field}.source_ids must be a list of strings")
        elif any(r not in ids for r in refs):
            errors.append(f"{field} references absent evidence")
    if errors:
        return errors
    comp = case["compensation"]
    pay_states = {"confirmed_paid", "likely_paid", "expenses_only", "confirmed_unpaid", "mixed_by_session_type", "unknown", "pay_to_speak"}
    if comp.get("status") not in pay_states:
        errors.append("invalid compensation status")
    if comp.get("status") == "confirmed_paid":
        if comp.get("speaker_context_checked") is not True or not any(s in public_checked for s in comp.get("source_ids", [])):
            errors.append("confirmed_paid requires checked speaker-compensation evidence")
    for field in ("event_date", "cfp_deadline"):
        if case.get(field):
            try:
                date.fromisoformat(case[field])
            except (ValueError, TypeError):
                errors.append(f"{field} must be a date-only ISO value or null")
    contacts = case.get("contacts", [])
    if not isinstance(contacts, list) or not all(isinstance(c, dict) for c in contacts):
        return errors + ["contacts must be a list of objects"]
    if case["route"].get("type") == "named_actionable":
        matching = [c for c in contacts if c.get("id") == case["route"].get("contact_id")]
        if len(matching) != 1 or not all(matching[0].get(k) is True for k in ("identity_supported", "role_supported", "channel_supported")):
            errors.append("named_actionable requires one identified candidate with role and owned-channel evidence")
        elif matching[0].get("historical") or not any(s in public_checked for s in matching[0].get("source_ids", [])):
            errors.append("named_actionable needs checked current evidence")
        elif not any(matching[0].get(k) for k in ("email", "linkedin", "phone", "booking_url")):
            errors.append("named_actionable needs the actual owned channel value")
    accepted = case.get("qualification") == "accepted"
    if case.get("qualification") not in {"accepted", "research_hold", "rejected", "watchlist"}:
        errors.append("invalid qualification")
    if accepted:
        if case["fit"].get("verdict") != "matched" or case["eligibility"].get("status") != "eligible":
            errors.append("accepted requires matched fit and confirmed eligibility")
        for field in ("fit", "eligibility"):
            if not any(s in public_checked for s in case[field].get("source_ids", [])):
                errors.append(f"accepted {field} needs checked evidence")
        if case["route"].get("type") not in {"named_actionable", "organizer_route", "application"} or not case["route"].get("purpose_checked"):
            errors.append("accepted requires a purpose-checked usable route")
        if not any(s in public_checked for s in case["route"].get("source_ids", [])):
            errors.append("accepted route needs checked evidence")
        if case["route"].get("type") in {"organizer_route", "application"} and not any(case["route"].get(k) for k in ("url", "email", "phone")):
            errors.append("accepted route needs its actual URL, email or phone")
        if case["kind"] == "conference":
            if not case.get("event_date") or case.get("cfp_status") == "Closed":
                errors.append("accepted conference needs a date and must not have a closed CFP")
        if paid_only and comp.get("status") != "confirmed_paid":
            errors.append("paid-only acceptance requires confirmed_paid")
        if paid_only and minimum_fee is not None:
            amount = comp.get("amount_min")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < minimum_fee or not math.isfinite(amount):
                errors.append("minimum fee is not established")
            if not currency or comp.get("currency") != currency:
                errors.append("minimum fee currency is not established")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("queries")
    q.add_argument("--keyword", action="append", default=[])
    q.add_argument("--geography", default="")
    q.add_argument("--as-of", required=True)
    score = sub.add_parser("score")
    score.add_argument("kind", choices=["podcast", "conference-legacy"])
    score.add_argument("file", type=Path)
    val = sub.add_parser("validate")
    val.add_argument("file", type=Path)
    val.add_argument("--paid-only", action="store_true")
    val.add_argument("--minimum-fee", type=float)
    val.add_argument("--currency")
    ident = sub.add_parser("identity")
    ident.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "queries":
            result = queries(args.keyword, args.geography, args.as_of)
        else:
            data = json.loads(args.file.read_text())
            if args.command == "score":
                result = (score_podcast if args.kind == "podcast" else score_conference)(data)
            elif args.command == "identity":
                result = {"case_key": identity(data)}
            else:
                errors = validate(data, args.paid_only, args.minimum_fee, args.currency)
                result = {"valid_structure": not errors, "errors": errors,
                          "factual_verification": "requires source review"}
                print(json.dumps(result, indent=2)); return 1 if errors else 0
        print(json.dumps(result, indent=2)); return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Invalid input: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
