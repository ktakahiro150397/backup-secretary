from __future__ import annotations

from datetime import datetime, timezone
from string import Formatter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .collector import CodexUsageSnapshot
from .presence_config import PresenceConfig


ALLOWED_PLACEHOLDERS = frozenset(
    {
        "remaining_percent",
        "used_percent",
        "reset_time_jst",
        "window_minutes",
        "latest_date",
        "latest_tokens",
        "latest_tokens_short",
    }
)


class RenderError(ValueError):
    """A safe rendering failure that contains no account data."""


def format_tokens(tokens: int | None) -> str:
    if tokens is None:
        return "?"
    value = max(0, int(tokens))
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if value >= divisor:
            number = value / divisor
            rendered = f"{number:.1f}".rstrip("0").rstrip(".")
            return f"{rendered}{suffix}"
    return str(value)


def _reset_time(reset_at: int | None, timezone_name: str) -> str:
    if reset_at is None:
        return "?"
    try:
        zone = ZoneInfo(timezone_name)
        instant = datetime.fromtimestamp(reset_at, tz=timezone.utc).astimezone(zone)
    except (ValueError, OverflowError, OSError, ZoneInfoNotFoundError):
        raise RenderError("invalid reset time or timezone") from None
    return instant.strftime("%m/%d %H:%M")


def _validate_template(template: str) -> None:
    try:
        parsed = Formatter().parse(template)
        for _, field_name, format_spec, conversion in parsed:
            if field_name is None:
                continue
            if field_name not in ALLOWED_PLACEHOLDERS or format_spec or conversion:
                raise RenderError("unsupported template placeholder")
    except ValueError as exc:
        if isinstance(exc, RenderError):
            raise
        raise RenderError("invalid template") from None


def render_presence(snapshot: CodexUsageSnapshot | None, config: PresenceConfig) -> str:
    if config.mode == "static":
        return config.static_text[: config.max_length]
    if snapshot is None:
        raise RenderError("usage snapshot unavailable")

    _validate_template(config.template)
    values = {
        "remaining_percent": "?" if snapshot.remaining_percent is None else snapshot.remaining_percent,
        "used_percent": "?" if snapshot.used_percent is None else snapshot.used_percent,
        "reset_time_jst": _reset_time(snapshot.reset_at, config.timezone),
        "window_minutes": "?" if snapshot.window_minutes is None else snapshot.window_minutes,
        "latest_date": snapshot.latest_date or "?",
        "latest_tokens": "?" if snapshot.latest_tokens is None else snapshot.latest_tokens,
        "latest_tokens_short": format_tokens(snapshot.latest_tokens),
    }
    try:
        text = config.template.format_map(values)
    except (KeyError, ValueError):
        raise RenderError("invalid template") from None
    return text[: config.max_length]


def build_custom_activity(text: str):
    import discord

    return discord.CustomActivity(name=text)
