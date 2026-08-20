from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

try:
    from agent.account_usage import fetch_account_usage
except Exception:  # pragma: no cover - exercised by the Hermes import smoke
    fetch_account_usage = None


class CollectionError(RuntimeError):
    """A sanitized Hermes usage collection failure."""


@dataclass(frozen=True)
class CodexUsageSnapshot:
    used_percent: int | None = None
    remaining_percent: int | None = None
    reset_at: int | None = None
    window_minutes: int | None = None
    latest_date: str | None = None
    latest_tokens: int | None = None
    fetched_at: float = 0.0


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _reset_epoch(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, datetime):
        instant = value
    elif isinstance(value, (int, float)):
        number = _finite_number(value)
        return None if number is None else int(number)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            instant = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None

    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    try:
        return int(instant.timestamp())
    except (OverflowError, OSError, ValueError):
        return None


def _select_usage_window(account_snapshot: Any) -> Any | None:
    windows = getattr(account_snapshot, "windows", None)
    if not isinstance(windows, (tuple, list)):
        return None

    usable = [window for window in windows if window is not None]
    for window in usable:
        label = str(getattr(window, "label", "") or "").strip().casefold()
        if label == "session":
            return window
    return usable[0] if usable else None


def _map_account_usage(
    account_snapshot: Any,
    *,
    now_fn: Callable[[], float],
) -> CodexUsageSnapshot:
    if account_snapshot is None:
        raise CollectionError("Hermes usage API returned no snapshot")

    provider = str(getattr(account_snapshot, "provider", "") or "").strip().lower()
    if provider != "openai-codex":
        raise CollectionError("Hermes usage API returned an unexpected provider")
    if getattr(account_snapshot, "unavailable_reason", None):
        raise CollectionError("Hermes usage API reported unavailable usage")

    window = _select_usage_window(account_snapshot)
    if window is None:
        raise CollectionError("Hermes usage API returned no rate-limit window")

    used_number = _finite_number(getattr(window, "used_percent", None))
    if used_number is None:
        raise CollectionError("Hermes usage API returned no usage percentage")
    used = min(100, max(0, round(used_number)))

    return CodexUsageSnapshot(
        used_percent=used,
        remaining_percent=100 - used,
        reset_at=_reset_epoch(getattr(window, "reset_at", None)),
        # Hermes' public usage snapshot exposes the window label and reset
        # time, but not the app-server's duration field.
        window_minutes=None,
        # The Hermes HTTP usage API intentionally exposes rate-limit windows,
        # not the app-server daily token buckets.
        latest_date=None,
        latest_tokens=None,
        fetched_at=float(now_fn()),
    )


def fetch_codex_snapshot(
    usage_fetcher: Callable[[str], Any] | None = None,
    *,
    now_fn: Callable[[], float] = time.time,
) -> CodexUsageSnapshot:
    """Read Codex usage through Hermes' active credential and usage API.

    The public Hermes helper resolves the current credential pool and performs
    the bounded HTTP request. This plugin deliberately does not invoke the
    standalone Codex CLI or its app-server authentication.
    """
    fetcher = usage_fetcher or fetch_account_usage
    if fetcher is None:
        raise CollectionError("Hermes usage API import unavailable")

    try:
        account_snapshot = fetcher("openai-codex")
    except Exception as exc:
        raise CollectionError(f"{type(exc).__name__}: Hermes usage read failed") from None

    return _map_account_usage(account_snapshot, now_fn=now_fn)
