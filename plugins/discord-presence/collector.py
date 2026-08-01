from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Mapping


RATE_LIMITS_READ_METHOD = "account/rateLimits/read"
USAGE_READ_METHOD = "account/usage/read"
READ_METHODS = frozenset({RATE_LIMITS_READ_METHOD, USAGE_READ_METHOD})


class CollectionError(RuntimeError):
    """A sanitized Codex usage collection failure."""


@dataclass(frozen=True)
class CodexUsageSnapshot:
    used_percent: int | None = None
    remaining_percent: int | None = None
    reset_at: int | None = None
    window_minutes: int | None = None
    latest_date: str | None = None
    latest_tokens: int | None = None
    fetched_at: float = 0.0


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _select_rate_limit(raw: Mapping[str, Any], bucket_id: str) -> Mapping[str, Any]:
    buckets = raw.get("rateLimitsByLimitId")
    if isinstance(buckets, Mapping):
        selected = buckets.get(bucket_id)
        if isinstance(selected, Mapping):
            return selected
    fallback = raw.get("rateLimits")
    return fallback if isinstance(fallback, Mapping) else {}


def _latest_daily_bucket(raw: Mapping[str, Any]) -> tuple[str | None, int | None]:
    buckets = raw.get("dailyUsageBuckets")
    if not isinstance(buckets, list):
        return None, None

    valid: list[tuple[str, int]] = []
    for bucket in buckets:
        if not isinstance(bucket, Mapping):
            continue
        start_date = bucket.get("startDate")
        tokens = _int_or_none(bucket.get("tokens"))
        if not isinstance(start_date, str) or tokens is None or tokens < 0:
            continue
        try:
            date.fromisoformat(start_date)
        except ValueError:
            continue
        valid.append((start_date, tokens))
    return max(valid, default=(None, None), key=lambda item: item[0])


def create_interruptible_codex_client(
    codex_bin: str = "codex",
    *,
    base_class: type | None = None,
):
    """Create a client whose close wakes synchronous pending requests.

    ``CodexAppServerClient.request`` blocks on a queue. Merely cancelling the
    asyncio wrapper does not stop that worker thread, so shutdown explicitly
    terminates the child process and injects a sanitized error into each
    pending queue.
    """
    if base_class is None:
        from agent.transports.codex_app_server import CodexAppServerClient

        base_class = CodexAppServerClient

    class InterruptibleCodexAppServerClient(base_class):
        def close(self, timeout: float = 0.5) -> None:
            pending = []
            lock = getattr(self, "_pending_lock", None)
            pending_map = getattr(self, "_pending", None)
            if lock is not None and isinstance(pending_map, dict):
                with lock:
                    pending = list(pending_map.values())
                    pending_map.clear()
            try:
                super().close(timeout=timeout)
            finally:
                message = {
                    "error": {
                        "code": -32000,
                        "message": "Codex usage client closed",
                    }
                }
                for request in pending:
                    try:
                        request.queue.put_nowait(message)
                    except Exception:
                        pass

    return InterruptibleCodexAppServerClient(codex_bin=codex_bin)


def _default_client_factory():
    return create_interruptible_codex_client()


def fetch_codex_snapshot(
    client_factory: Callable[[], Any] | None = None,
    *,
    bucket_id: str = "codex",
    timeout: float = 15.0,
    now_fn: Callable[[], float] = time.time,
) -> CodexUsageSnapshot:
    factory = client_factory or _default_client_factory
    try:
        with factory() as client:
            client.initialize(
                client_name="hermes-discord-presence",
                client_title="Hermes Discord Presence",
                client_version="1.0.1",
            )
            rate_limits = client.request(RATE_LIMITS_READ_METHOD, timeout=timeout)
            usage = client.request(USAGE_READ_METHOD, timeout=timeout)
    except Exception as exc:
        raise CollectionError(f"{type(exc).__name__}: Codex usage read failed") from None

    if not isinstance(rate_limits, Mapping):
        rate_limits = {}
    if not isinstance(usage, Mapping):
        usage = {}

    selected = _select_rate_limit(rate_limits, bucket_id)
    primary = selected.get("primary") if isinstance(selected, Mapping) else None
    if not isinstance(primary, Mapping):
        primary = {}

    used = _int_or_none(primary.get("usedPercent"))
    if used is not None:
        used = min(100, max(0, used))
    remaining = None if used is None else 100 - used
    latest_date, latest_tokens = _latest_daily_bucket(usage)

    return CodexUsageSnapshot(
        used_percent=used,
        remaining_percent=remaining,
        reset_at=_int_or_none(primary.get("resetsAt")),
        window_minutes=_int_or_none(primary.get("windowDurationMins")),
        latest_date=latest_date,
        latest_tokens=latest_tokens,
        fetched_at=float(now_fn()),
    )
