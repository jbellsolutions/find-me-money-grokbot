#!/usr/bin/env python3
"""Assemble the Hermes profile distributions for this machine into build/profiles/<name>/.

Each one gets its distribution.yaml, SOUL.md, cron/jobs.json, its skills from skills-src/, and a config.yaml
rendered for this machine (the Python its MCP server runs on, this repo, its home folder, the box URLs). The
build folder is gitignored; install it with `hermes profile install build/profiles/<name>`.

    python3 scripts/build_profiles.py                  # both officers, Justin's Mac: real-profile browsing off
    python3 scripts/build_profiles.py --orgo           # the officers' own Orgo computer: portals' Chrome profile on
    python3 scripts/build_profiles.py --profiles pinnacle-reply-agent   # the Reply Agent only (its own venv)
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OFFICERS = ["funding-intake-officer", "loan-processing-officer"]
REPLY = "pinnacle-reply-agent"
PROFILES = [*OFFICERS, REPLY]
# The Reply Agent needs no GHL, browser or funding-director skills: only its own loop and the charter's agent brief.
SKILLS = {REPLY: ["pinnacle/DESCRIPTION.md", "pinnacle/reply-agent", "pinnacle/find-me-money-charter"]}
# HERMES_PYTHON (env) wins; then the usual install places, relative to the home folder or the system install.
HERMES_PYTHONS = [*([Path(os.environ["HERMES_PYTHON"])] if os.environ.get("HERMES_PYTHON") else []),
                  Path.home() / ".hermes/hermes-agent/venv/bin/python", Path.home() / "hermes-agent/.venv/bin/python",
                  Path("/opt/hermes/.venv/bin/python")]


def _default_python() -> str:
    for candidate in HERMES_PYTHONS:
        if candidate.exists():
            return str(candidate)
    raise SystemExit("can't find the Hermes virtualenv Python; pass --hermes-python")


def _env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def build(args: argparse.Namespace) -> list[Path]:
    officer_home = Path(args.officer_home).expanduser()
    reply_home = Path(args.reply_home).expanduser()
    local = _env_file(officer_home / "officer.env")
    names = args.profiles or OFFICERS
    unknown = set(names) - set(PROFILES)
    if unknown:
        raise SystemExit(f"unknown profile(s): {', '.join(sorted(unknown))}")
    values = {
        "__HERMES_PYTHON__": (args.hermes_python or _default_python()) if set(names) & set(OFFICERS) else "",
        "__REPLY_PYTHON__": args.reply_python or str(reply_home / "venv" / "bin" / "python"),
        "__REPLY_HOME__": str(reply_home),
        "__REPO__": str(REPO),
        "__OFFICER_HOME__": str(officer_home),
        "__FD_SRC__": str(officer_home / "brain" / "fd-src"),
        "__GHL_BIN__": args.ghl_bin,
        "__USE_REAL_PROFILE__": "true" if args.orgo else "false",
        "__REAL_PROFILE_PIN__": args.real_profile_pin if args.orgo else "",
        "__BROWSER_BOX_URL__": os.environ.get("BROWSER_BOX_URL") or local.get("BROWSER_BOX_URL", ""),
        "__DATABOX_URL__": os.environ.get("DATABOX_URL") or local.get("DATABOX_URL", ""),
    }
    out_dirs = []
    for name in names:
        src, out = REPO / "profiles" / name, Path(args.out) / name
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        for item in ("distribution.yaml", "SOUL.md"):
            shutil.copy2(src / item, out / item)
        shutil.copytree(src / "cron", out / "cron")
        config = (src / "config.template.yaml").read_text(encoding="utf-8")
        for key, value in values.items():
            config = config.replace(key, value)
        if not values["__BROWSER_BOX_URL__"]:
            config = _drop_server(config, "browser-box")
        if not values["__DATABOX_URL__"]:
            config = _drop_server(config, "data-box")
        (out / "config.yaml").write_text(config, encoding="utf-8")
        if name in SKILLS:
            for rel in SKILLS[name]:
                source, dest = REPO / "skills-src" / rel, out / "skills" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".DS_Store"))
                else:
                    shutil.copy2(source, dest)
        else:
            shutil.copytree(REPO / "skills-src", out / "skills", ignore=shutil.ignore_patterns(".DS_Store"))
        out_dirs.append(out)
    return out_dirs


def _drop_server(config: str, server: str) -> str:
    """Remove an MCP server block (and its toolset line) when its URL isn't configured on this machine."""
    lines, out, skipping = config.splitlines(), [], False
    for line in lines:
        if line.startswith(f"  {server}:"):
            skipping = True
            continue
        if skipping and (line.startswith("  ") and not line.startswith("   ") and line.strip()):
            skipping = False
        if skipping:
            continue
        if line.strip() == f"- mcp-{server}":
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--profiles", nargs="+", choices=PROFILES, help="which to build (default: both officers)")
    p.add_argument("--hermes-python", default="")
    p.add_argument("--reply-python", default="", help="the Reply Agent venv's Python (default $REPLY_HOME/venv)")
    p.add_argument("--reply-home", default=os.environ.get("REPLY_HOME", str(Path.home() / ".pinnacle-reply")))
    p.add_argument("--out", default=str(REPO / "build" / "profiles"), help="where the assembled profiles go")
    p.add_argument("--officer-home", default=os.environ.get("OFFICER_HOME", str(Path.home() / ".pinnacle-officer")))
    # ghl-super-hub's installer puts its CLI at ~/.local/bin/ghl; bootstrap builds before it's installed, so a bare
    # "ghl" would depend on the PATH Hermes gives its MCP servers.
    p.add_argument("--ghl-bin", default=shutil.which("ghl") or str(Path.home() / ".local/bin/ghl"))
    p.add_argument("--orgo", action="store_true", help="the officer's own computer: drive the portals' Chrome profile")
    p.add_argument("--real-profile-pin", default="Default", help="Chrome profile directory the portals are signed into")
    for path in build(p.parse_args()):
        print(path)


if __name__ == "__main__":
    main()
