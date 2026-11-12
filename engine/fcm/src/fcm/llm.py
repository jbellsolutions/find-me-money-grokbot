"""A small OpenRouter chat client for the work that runs outside the Hermes loop: drafting kickoff
texts in waves, pulling facts out of replies and call transcripts, and drafting revenue plans.

    FCM_DRAFT_MODEL=openai/gpt-6-luna-pro   (FCM_FALLBACK_MODEL=z-ai/glm-5.3-flash)
    OPENROUTER_API_KEY=...

Off unless FCM_DRAFT_MODEL and OPENROUTER_API_KEY are both set. Every caller has a deterministic
fallback (templates and keyword rules), so the agent never stalls on a model outage. Requests ask
OpenRouter to route only to providers that don't keep or train on the data.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any
from urllib import error, request

from .errors import FcmError

URL = "https://openrouter.ai/api/v1/chat/completions"


def enabled() -> bool:
    return bool(os.getenv("FCM_DRAFT_MODEL", "").strip() and os.getenv("OPENROUTER_API_KEY", "").strip())


class LLM:
    def __init__(self, model: str = "", fallback: str = ""):
        self.key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.model = model or os.getenv("FCM_DRAFT_MODEL", "").strip()
        self.fallback = fallback or os.getenv("FCM_FALLBACK_MODEL", "z-ai/glm-5.3-flash").strip()
        if not self.key or not self.model:
            raise FcmError("model drafting needs OPENROUTER_API_KEY and FCM_DRAFT_MODEL")
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    def chat(self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.4) -> str:
        last: Exception | None = None
        for model in (self.model, self.fallback):
            for attempt in range(2):
                try:
                    return self._once(model, system, user, max_tokens, temperature)
                except FcmError as exc:
                    last = exc
                    time.sleep(1.5 * (attempt + 1))
        raise FcmError(f"model call failed: {last}")

    def _once(self, model: str, system: str, user: str, max_tokens: int, temperature: float) -> str:
        body = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
                "provider": {"data_collection": "deny"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        req = request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
            "Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
            "X-Title": "Funding CRM Manager"})
        try:
            with request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read(2_000_000))
        except error.HTTPError as exc:
            raise FcmError(f"OpenRouter returned HTTP {exc.code}") from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise FcmError("OpenRouter could not be reached") from exc
        usage = data.get("usage") or {}
        self.usage["calls"] += 1
        self.usage["input_tokens"] += int(usage.get("prompt_tokens") or 0)
        self.usage["output_tokens"] += int(usage.get("completion_tokens") or 0)
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise FcmError("OpenRouter returned no message") from exc
        return text.strip()

    def chat_json(self, system: str, user: str, **kwargs: Any) -> dict[str, Any]:
        """One JSON object. A cut-off or malformed answer is retried once with twice the token budget
        (reasoning models spend part of max_tokens thinking)."""
        for _ in range(2):
            text = self.chat(system + "\nReply with one JSON object and nothing else.", user, **kwargs)
            match = re.search(r"\{.*\}", text, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            kwargs["max_tokens"] = int(kwargs.get("max_tokens", 600)) * 2
        raise FcmError("model did not return valid JSON")
