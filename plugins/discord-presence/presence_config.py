from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


SUPPORTED_MODES = frozenset({"rate_limit", "daily_tokens", "combined", "static"})
DEFAULT_TEMPLATE = "Codex残量 {remaining_percent}%｜次回リセット {reset_time_jst}"


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _as_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class PresenceConfig:
    enabled: bool = False
    mode: str = "rate_limit"
    template: str = DEFAULT_TEMPLATE
    bucket_id: str = "codex"
    refresh_seconds: int = 300
    stale_after_seconds: int = 900
    fallback_text: str = "Codex利用量 取得待ち"
    timezone: str = "Asia/Tokyo"
    max_length: int = 120
    static_text: str = "Hermes"
    validation_errors: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "PresenceConfig":
        if not isinstance(raw, Mapping):
            return cls()

        errors: list[str] = []
        mode_value = str(raw.get("mode", cls.mode)).strip().lower()
        if mode_value not in SUPPORTED_MODES:
            errors.append(f"unsupported mode: {mode_value}")
            mode_value = cls.mode

        refresh = max(60, _as_int(raw.get("refresh_seconds"), cls.refresh_seconds))
        stale = max(refresh, _as_int(raw.get("stale_after_seconds"), cls.stale_after_seconds))
        max_length = min(120, max(1, _as_int(raw.get("max_length"), cls.max_length)))

        return cls(
            enabled=_as_bool(raw.get("enabled"), cls.enabled),
            mode=mode_value,
            template=str(raw.get("template", cls.template)),
            bucket_id=str(raw.get("bucket_id", cls.bucket_id)).strip() or cls.bucket_id,
            refresh_seconds=refresh,
            stale_after_seconds=stale,
            fallback_text=str(raw.get("fallback_text", cls.fallback_text)),
            timezone=str(raw.get("timezone", cls.timezone)).strip() or cls.timezone,
            max_length=max_length,
            static_text=str(raw.get("static_text", cls.static_text)),
            validation_errors=tuple(errors),
        )


def load_presence_config(
    config_loader: Callable[[], Mapping[str, Any]] | None = None,
) -> PresenceConfig:
    if config_loader is None:
        from hermes_cli.config import load_config

        config_loader = load_config

    try:
        root = config_loader()
    except Exception:
        return PresenceConfig()
    if not isinstance(root, Mapping):
        return PresenceConfig()
    discord_cfg = root.get("discord")
    if not isinstance(discord_cfg, Mapping):
        return PresenceConfig()
    presence_cfg = discord_cfg.get("presence")
    if not isinstance(presence_cfg, Mapping):
        return PresenceConfig()
    return PresenceConfig.from_mapping(presence_cfg)
