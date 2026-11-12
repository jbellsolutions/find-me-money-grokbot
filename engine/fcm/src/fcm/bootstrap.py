"""Idempotent GHL setup for a Funding Affiliate Manager location.

Creates what the public API allows (custom fields, tags, custom values) and maps what
must be built by hand or on the Orgo desktop (pipelines, workflows) by exact name.
Writes every id into config/ghl-map.json. Safe to re-run: existing items are reused.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .config import Settings
from .errors import FcmError
from .ghl import LiveGHL


def _load(settings: Settings, name: str) -> Any:
    return json.loads((settings.config_dir / name).read_text())


def bootstrap(settings: Settings, dry_run: bool = True) -> dict[str, Any]:
    if settings.ghl_mode != "live":
        raise FcmError("bootstrap runs against a live location (FCM_GHL_MODE=live)")
    ghl_map = dict(settings.ghl_map)
    location_id = os.getenv("GHL_LOCATION_ID", "").strip()
    if ghl_map.get("location_id") and ghl_map["location_id"] != location_id:
        raise FcmError("GHL_LOCATION_ID differs from config/ghl-map.json — refusing to bootstrap another location")
    ghl = LiveGHL(expected_location_id=ghl_map.get("location_id", ""))
    report: dict[str, Any] = {"location": ghl.location().get("name", ""), "location_id": ghl.location_id,
                              "dry_run": dry_run, "created": [], "mapped": [], "missing_manual": []}

    # custom fields
    existing = {f.get("name"): f for f in ghl.list_custom_fields()}
    field_ids = dict(ghl_map.get("custom_fields", {}))
    for spec in _load(settings, "custom-fields.json")["fields"]:
        if spec["name"] in existing:
            field_ids[spec["key"]] = existing[spec["name"]]["id"]
            report["mapped"].append(f"field {spec['name']}")
        elif dry_run:
            report["created"].append(f"(would create) field {spec['name']}")
        else:
            created = ghl.create_custom_field(spec["name"], spec["dataType"], spec.get("options"))
            field_ids[spec["key"]] = created.get("id", "")
            report["created"].append(f"field {spec['name']}")

    # tags
    have_tags = {t.get("name") for t in ghl.list_tags()}
    taxonomy = _load(settings, "tag-taxonomy.json")
    for group in ("source", "lifecycle", "interest", "system", "tier", "kickoff", "memory", "contact_limits"):
        for tag in taxonomy.get(group, []):
            if tag in have_tags:
                continue
            if dry_run:
                report["created"].append(f"(would create) tag {tag}")
            else:
                ghl.create_tag(tag)
                report["created"].append(f"tag {tag}")

    # custom values
    have_values = {v.get("name") for v in ghl.list_custom_values()}
    for name in _load(settings, "custom-values.json")["names"]:
        if name in have_values:
            continue
        if dry_run:
            report["created"].append(f"(would create) custom value {name}")
        else:
            ghl.update_custom_value_by_name(name, "-")
            report["created"].append(f"custom value {name}")

    # pipelines (manual build, mapped by exact name)
    pipelines = {p.get("name"): p for p in ghl.list_pipelines()}
    mapped_pipelines = dict(ghl_map.get("pipelines", {}))
    for key, spec in _load(settings, "pipelines.json").items():
        if key.startswith("_"):
            continue
        found = pipelines.get(spec["name"])
        if not found:
            report["missing_manual"].append(f"pipeline '{spec['name']}' with stages {spec['stage_names']}")
            continue
        stage_by_name = {s.get("name"): s.get("id") for s in found.get("stages", [])}
        stages = {k: stage_by_name.get(n, "") for k, n in zip(spec["stages"], spec["stage_names"])}
        missing = [n for k, n in zip(spec["stages"], spec["stage_names"]) if not stages[k]]
        if missing:
            report["missing_manual"].append(f"pipeline '{spec['name']}' is missing stages {missing}")
        mapped_pipelines[key] = {"id": found["id"], "stages": stages}
        report["mapped"].append(f"pipeline {spec['name']}")

    # workflows (manual build, mapped by exact name)
    workflows = {w.get("name"): w for w in ghl.list_workflows()}
    mapped_workflows = dict(ghl_map.get("workflows", {}))
    for key, spec in _load(settings, "workflows.json").items():
        if key.startswith("_"):
            continue
        found = workflows.get(spec["name"])
        if found:
            mapped_workflows[key] = found["id"]
            report["mapped"].append(f"workflow {spec['name']} ({found.get('status', '?')})")
        else:
            report["missing_manual"].append(f"workflow '{spec['name']}' — {spec['steps']}")

    # manager user for task assignment
    users = ghl.list_users()
    wanted = os.getenv("FCM_MANAGER_USER_NAME", "").strip().lower()
    manager = next((u for u in users if wanted and wanted in (u.get("name") or "").lower()), {})

    ghl_map.update({
        # The id itself stays out of the pack: the file keeps the env reference (config.resolve_env reads it).
        "location_id": "<PINNACLE_GHL_LOCATION_ID>" if os.getenv("PINNACLE_GHL_LOCATION_ID", "").strip() == ghl.location_id
        else ghl.location_id,
        "custom_fields": field_ids,
        "pipelines": mapped_pipelines,
        "workflows": mapped_workflows,
        "users": {"manager": manager.get("id", "")},
    })
    if not dry_run:
        (settings.config_dir / "ghl-map.json").write_text(json.dumps(ghl_map, indent=2) + "\n")
    report["ghl_map"] = {k: (len(v) if isinstance(v, dict) else v) for k, v in ghl_map.items() if k != "_comment"}
    return report
