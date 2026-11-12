"""Runtime configuration: paths, GHL map, cadence rules, and policy.

Everything that differs between a demo location and a client location lives in
config/*.json or the environment, so duplicating the system is a config change.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import FcmError

PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # files/local-packages/fcm
REPO_ROOT = PACKAGE_ROOT.parents[2]  # repo root when running from a checkout

CUSTOM_FIELD_KEYS = (
    "affiliate_id",
    "join_date",
    "source",
    "niche",
    "audience_size",
    "deals_submitted",
    "last_deal_date",
    "funded_volume",
    "last_touch_date",
    "last_touch_channel",
    "last_offer_date",
    "last_reply_date",
    "next_touch_date",
    "cadence_note",
    "preferred_channel",
    "assigned_manager",
    "products_of_interest",
    "services_offered",
    "obsidian_note",
    "tier",
    "plan",
    "profile_summary",
    "profile_completeness",
    "next_step",
    "client_types",
    "deal_types",
    "deal_size",
    "regions",
    "goals",
    "best_time",
    "blockers",
    "needs",
    "next_question",
    "open_loops",
    "calls_held",
    "revenue_plan",
    "kickoff_variant",
    "file_line",
    "history_line",
    "referral_link",
)

DEFAULT_CADENCE: dict[str, Any] = {
    "onboarding_days": 14,
    "biweekly_touch_days": 14,
    "monthly_offer_days": 30,
    "quiet_after_days": 45,
    "checkin_after_days": 60,
    "dormant_after_days": 90,
    "dead_after_days": 180,
    "dead_reactivation_every_days": 90,
    "sms_window_start_hour": 9,  # the recipient's local time
    "sms_window_end_hour": 20,
    "daily_personal_touch_cap": 40,
    "daily_bulk_enroll_cap": 2000,
    "batch_approval_max": 100,
    "approval_ttl_hours": 12,
    "resume_ttl_hours": 36,
    "action_ttl_hours": 48,
    "inbox_lookback_days": 14,
    "timezone": "America/New_York",
}

DEFAULT_KICKOFF: dict[str, Any] = {
    "company": "Find Me Money Group",
    "default_sender": "Justin",
    "generic_manager_names": ["Funding Relationship Manager", "Partner Manager", ""],
    "wave_size": 250,
    "batch_max": 500,
    "max_segments": 2,
    "nudge_after_days": 5,
    "variants": ["A", "B", "C"],
    "calendar_link": "",
    "mailing_address": "",
    "send_pause_seconds": 1.0,
    "program_tags": {},
}


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser() if value else default


_ENV_REF = re.compile(r"^<([A-Z][A-Z0-9_]*)>$")


def resolve_env(value: Any) -> Any:
    """Replace every string that is exactly `<NAME>` with env NAME. Private ids (locations, workflows) never ship in
    the config files; they are set at intake. An unset NAME stays `<NAME>`, which never equals a real id, so every
    check against it refuses (fail closed)."""
    if isinstance(value, dict):
        return {k: resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_env(v) for v in value]
    if isinstance(value, str):
        m = _ENV_REF.match(value)
        if m:
            return os.getenv(m.group(1), "").strip() or value
    return value


def unresolved(value: Any) -> bool:
    return isinstance(value, str) and bool(_ENV_REF.match(value))


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return resolve_env(json.loads(path.read_text()))
    except json.JSONDecodeError as exc:
        raise FcmError(f"{path.name} is not valid JSON: {exc}") from exc


@dataclass
class Settings:
    config_dir: Path
    state_dir: Path
    vault_dir: Path
    policy_path: Path
    ghl_mode: str
    demo_mode: bool
    profile: str
    crm: str = "ghl"        # where lead records live
    channel: str = "ghl"    # ghl | relay | twilio: how real texts go out when the CRM can't send them
    ghl_map: dict[str, Any] = field(default_factory=dict)
    cadence: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    kickoff: dict[str, Any] = field(default_factory=dict)
    profile_schema: dict[str, Any] = field(default_factory=dict)
    # Optional install settings (config/client.json).
    client: dict[str, Any] = field(default_factory=dict)

    @property
    def knowledge_pack(self) -> str:
        return str(self.client.get("knowledge_pack") or "lending")

    def knowledge(self, name: str = "") -> str:
        """The repo-relative path of a knowledge file in this client's pack, e.g. knowledge/lending/01-…md."""
        return f"knowledge/{self.knowledge_pack}/{name}".rstrip("/")

    @classmethod
    def load(cls) -> "Settings":
        config_dir = _env_path("FCM_CONFIG_DIR", REPO_ROOT / "config")
        state_dir = _env_path("FCM_STATE_DIR", Path.home() / ".fcm" / "state")
        vault_dir = _env_path("FCM_VAULT_DIR", Path.home() / "fcm-vault")
        policy_path = _env_path("FCM_POLICY_PATH", REPO_ROOT / "policies" / "permissions.json")
        ghl_mode = os.getenv("FCM_GHL_MODE", "live").strip().lower() or "live"
        if ghl_mode not in {"live", "mock"}:
            raise FcmError("FCM_GHL_MODE must be 'live' or 'mock'")
        demo_mode = os.getenv("FCM_DEMO_MODE", "1").strip() not in {"0", "false", "no"}
        crm = os.getenv("FCM_CRM", "ghl").strip().lower() or "ghl"
        if crm != "ghl":
            raise FcmError("FCM_CRM must be 'ghl'")
        channel = os.getenv("FCM_CHANNEL", "").strip().lower() or ("ghl" if crm == "ghl" else "relay")
        if channel not in {"ghl", "relay", "twilio"}:
            raise FcmError("FCM_CHANNEL must be 'ghl', 'relay' or 'twilio'")
        ghl_map = _read_json(config_dir / "ghl-map.json", {})
        cadence = dict(DEFAULT_CADENCE)
        cadence.update(_read_json(config_dir / "cadence.json", {}))
        policy = _read_json(policy_path, {})
        kickoff = dict(DEFAULT_KICKOFF)
        kickoff.update({k: v for k, v in _read_json(config_dir / "kickoff.json", {}).items() if not k.startswith("_")})
        profile_schema = _read_json(config_dir / "profile-schema.json", {"slots": [], "sections": {}})
        client = _read_json(config_dir / "client.json", {})
        profile = os.getenv("FCM_GHL_PROFILE", "").strip() or str(ghl_map.get("profile", ""))
        state_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            config_dir=config_dir,
            state_dir=state_dir,
            vault_dir=vault_dir,
            policy_path=policy_path,
            ghl_mode=ghl_mode,
            demo_mode=demo_mode,
            profile=profile,
            crm=crm,
            channel=channel,
            ghl_map=ghl_map,
            cadence=cadence,
            policy=policy,
            kickoff=kickoff,
            profile_schema=profile_schema,
            client=client,
        )

    # ── GHL map helpers ────────────────────────────────────────────────────
    @property
    def logical_ids(self) -> bool:
        """The mock CRM takes the agent's own keys for fields, workflows and pipelines; only live
        GoHighLevel needs the ids from config/ghl-map.json."""
        return self.ghl_mode == "mock" or self.crm != "ghl"

    def field_id(self, key: str) -> str:
        """Return the GHL custom-field id for a logical key (mock mode uses the key)."""
        if self.logical_ids:
            return key
        ids = self.ghl_map.get("custom_fields", {})
        value = ids.get(key, "")
        if not value:
            raise FcmError(
                f"custom field '{key}' has no GHL id in config/ghl-map.json — run `fcm ghl bootstrap` first"
            )
        return value

    def program_tag(self, kind: str) -> str:
        """cohort / campaign / source from kickoff.json program_tags, lowercased the way GHL stores tags."""
        return str((self.kickoff.get("program_tags") or {}).get(kind) or "").strip().lower()

    @property
    def cohort_tag(self) -> str:
        """Every partner the agent manages carries it; the agent never reads the rest of the sub-account. Live GHL
        only: the mock backend holds synthetic demo and simulation populations with no cohort."""
        return self.program_tag("cohort") if self.ghl_mode == "live" and self.crm == "ghl" else ""

    def field_ids(self) -> dict[str, str]:
        if self.logical_ids:
            return {key: key for key in CUSTOM_FIELD_KEYS}
        return {k: v for k, v in self.ghl_map.get("custom_fields", {}).items() if v}

    def workflow_id(self, key: str) -> str:
        value = self.ghl_map.get("workflows", {}).get(key, "")
        if self.logical_ids:
            return value or f"w-{key}"
        if not value:
            raise FcmError(f"workflow '{key}' is not mapped in config/ghl-map.json")
        return value

    def pipeline(self, key: str) -> dict[str, Any]:
        pipelines = self.ghl_map.get("pipelines", {})
        value = pipelines.get(key) or {}
        if self.logical_ids and not value.get("id"):
            spec = _read_json(self.config_dir / "pipelines.json", {}).get(key, {})
            return {
                "id": f"pl-{key}",
                "stages": {stage: f"st-{key}-{stage}" for stage in spec.get("stages", [])},
            }
        if not value.get("id"):
            raise FcmError(f"pipeline '{key}' is not mapped in config/ghl-map.json")
        return value

    def policy_rule(self, action: str) -> dict[str, Any]:
        return self.policy.get("actions", {}).get(action, {})
