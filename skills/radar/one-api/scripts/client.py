#!/usr/bin/env python3
"""Portable One API client. Python standard library only; never follows redirects."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def connection():
    url, token = os.environ.get("ONE_API_URL"), os.environ.get("ONE_API_TOKEN")
    if url is not None or token is not None:
        if not url or not token:
            raise ValueError("Supply ONE_API_URL and ONE_API_TOKEN together")
    else:
        path = Path(os.environ.get("ONE_API_CONFIG", str(Path.home() / ".config/one-api/client.json")))
        if not path.exists():
            raise ValueError("Missing One API connection; configure it privately")
        settings = json.loads(path.read_text())
        url, token = settings["url"], settings["token"]
    parsed = urlsplit(url)
    if (parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"})) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("One API needs a private HTTPS origin, or local loopback HTTP")
    if not token:
        raise ValueError("Missing One API token")
    return url.rstrip("/"), token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover")
    sub.add_parser("tools")
    call = sub.add_parser("call")
    call.add_argument("tool")
    call.add_argument("--arguments", default="{}")
    call.add_argument("--request-id", required=True)
    call.add_argument("--goal-id")
    job = sub.add_parser("job")
    job.add_argument("job_id")
    args = parser.parse_args()
    try:
        url, token = connection()
        method, path, body = "GET", "/v1/capabilities", None
        if args.command == "discover":
            method, path, body = "POST", "/v1/discover", {}
        elif args.command == "call":
            method, path = "POST", "/v1/call"
            body = {"tool": args.tool, "arguments": json.loads(args.arguments), "request_id": args.request_id}
            if args.goal_id:
                body["goal_id"] = args.goal_id
        elif args.command == "job":
            path = "/v1/jobs/" + quote(args.job_id, safe="")
        req = Request(url + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                      headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with build_opener(NoRedirect).open(req, timeout=60) as response:
            print(json.dumps(json.load(response), indent=2))
    except HTTPError as exc:
        print(json.dumps({"error": "gateway_http_error", "http_status": exc.code}))
        return 1
    except (URLError, ValueError, KeyError, OSError):
        print(json.dumps({"error": "connection_or_request_unavailable", "next": "Inspect the private connection and retain the same request_id after a timeout"}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
