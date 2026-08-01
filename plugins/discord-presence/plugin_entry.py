from __future__ import annotations

from typing import Any

from .adapter import create_presence_adapter_class


def install_upstream_override(ctx: Any, *, upstream_module: Any = None) -> type:
    if upstream_module is None:
        from plugins.platforms.discord import adapter as upstream_module

    current_class = upstream_module.DiscordAdapter
    if getattr(current_class, "_discord_presence_plugin", False):
        installed_class = current_class
    else:
        installed_class = create_presence_adapter_class(current_class)
        installed_class._discord_presence_plugin = True
        upstream_module.DiscordAdapter = installed_class

    upstream_module.register(ctx)
    return installed_class


def register(ctx: Any) -> None:
    install_upstream_override(ctx)
