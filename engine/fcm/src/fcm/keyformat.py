"""What each key's value looks like, so a value pasted at the wrong prompt is caught at that prompt.

On 2026-10-20 a GoHighLevel pit- token went in at the Slack bot-token prompt. Every place a person types a key
checks it here: `deploy/orgo/set-secrets.py` asks again, `deploy/gate/launch.sh` refuses it (its own prefix list,
kept in step by tests/test_affiliate_os.py), and `fcm launch check` reports any that are already in agent.env.

Only keys with a fixed, published shape are listed. A key not listed is never refused. The value itself is never
printed: a message names the kind of token it looks like, nothing more.
"""

from __future__ import annotations

import re

_SLACK_IDS = r"[UW][A-Z0-9]{6,}(\s*,\s*[UW][A-Z0-9]{6,})*"
# key: (pattern the whole value must match, what it should be)
RULES: dict[str, tuple[str, str]] = {
    "GHL_API_KEY": (r"pit-\S+", "a GoHighLevel Private Integration token, pit-..."),
    "GATE_GHL_API_KEY": (r"pit-\S+", "a GoHighLevel Private Integration token, pit-..."),
    "SLACK_BOT_TOKEN": (r"xoxb-\S+", "the Slack app's Bot User OAuth Token, xoxb-..."),
    "GATE_SLACK_BOT_TOKEN": (r"xoxb-\S+", "the Slack app's Bot User OAuth Token, xoxb-..."),
    "SLACK_APP_TOKEN": (r"xapp-\S+", "the Slack app-level token, xapp-..."),
    # Hermes' /sethome can save a DM (D...) as home; the channel's name has its own key, SLACK_HOME_CHANNEL_NAME
    "SLACK_HOME_CHANNEL": (r"[CGD][A-Z0-9]{6,}", "a Slack channel id, C..."),
    "GATE_SLACK_CHANNEL": (r"[CG][A-Z0-9]{6,}", "a Slack channel id, C..."),
    # Hermes reads * as everyone. The gate has no such wildcard: its approvers are always named
    "SLACK_ALLOWED_USERS": (rf"\*|{_SLACK_IDS}", "Slack member ids, U..., comma-separated"),
    "GATE_APPROVER_SLACK_IDS": (_SLACK_IDS, "Slack member ids, U..., comma-separated"),
    "OPENROUTER_API_KEY": (r"sk-or-\S+", "an OpenRouter key, sk-or-..."),
    "FCM_SEND_GATE_URL": (r"https://\S+", "the send gate's https:// address"),
    "CLICKUP_API_TOKEN": (r"pk_\S+", "a ClickUp personal API token, pk_..."),
}
# What a misplaced value most likely is, by its prefix
_KINDS = (("pit-", "a GoHighLevel token"), ("xoxb-", "a Slack bot token"), ("xapp-", "a Slack app-level token"),
          ("xoxp-", "a Slack user token"), ("sk-or-", "an OpenRouter key"), ("https://", "a web address"), ("pk_", "a ClickUp token"))


def problem(key: str, value: str) -> str:
    """'' when the value fits the key (or the key has no rule, or the value is empty); else what's wrong."""
    value = (value or "").strip()
    rule = RULES.get(key)
    if not value or not rule or re.fullmatch(rule[0], value):
        return ""
    kind = next((k for p, k in _KINDS if value.startswith(p)), "")
    return (f"that looks like {kind}, not {key}" if kind else f"that doesn't look like {key}") + f": {rule[1]}"


def problems(env: dict[str, str]) -> dict[str, str]:
    """Every key in env whose value doesn't fit, with what's wrong. Comment-only values count as empty."""
    out = {}
    for key in RULES:
        why = problem(key, re.sub(r"(^|\s+)#.*$", "", env.get(key, "")))
        if why:
            out[key] = why
    return out
