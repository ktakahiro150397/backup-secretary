"""Read oMLX's current activity, independently of this bot's active turns."""
from __future__ import annotations

import json
import math
import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .presence_config import PresenceConfig


class ActivityError(RuntimeError):
    """No URLs, credentials, response bodies or request identifiers in errors."""


def render_activity(data: dict) -> str:
    active = data.get("active_models")
    if not isinstance(active, dict) or not isinstance(active.get("models"), list):
        raise ActivityError("Invalid oMLX activity")
    rates = []
    busy = False
    for model in active["models"]:
        if not isinstance(model, dict):
            raise ActivityError("Invalid oMLX model activity")
        busy |= bool(model.get("is_loading") or model.get("active_requests") or model.get("waiting_requests"))
        busy |= bool(model.get("prefilling") or model.get("generating"))
        for request in model.get("generating", []):
            rate = request.get("tokens_per_second") if isinstance(request, dict) else None
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate < 0:
                raise ActivityError("Invalid oMLX generation rate")
            rates.append(rate)
    # These are the native per-request dashboard rates. Sum concurrent rows;
    # never estimate throughput from token counts or a bot's elapsed time.
    if rates:
        return f"{sum(rates):.1f}tok/s"
    return "0.0tok/s" if busy else "idle"


def fetch_omlx_activity(config: PresenceConfig) -> str:
    try:
        parts = urlsplit(config.omlx_base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError()
        key = os.environ.get(config.omlx_key_env, "")
        if not key:
            raise ValueError()
        request = Request(config.omlx_base_url + "/admin/api/activity", headers={"Authorization": "Bearer " + key})
        # No browser cookies, stats endpoint, response logging or retries.
        with urlopen(request, timeout=4) as response:
            payload = response.read(1_048_577)
        if len(payload) > 1_048_576:
            raise ValueError()
        return render_activity(json.loads(payload))
    except Exception:
        raise ActivityError("oMLX activity unavailable") from None
