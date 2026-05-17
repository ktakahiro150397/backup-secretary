# docker/hermes/patches/discord_free_response_thread.py
"""
一時モンキーパッチ（PR #26074 相当）

free_response_channels でも auto_thread を効かせる。

次回 Hermes アプデで公式修正が入ったら、このファイルごと削除。
"""
import os
import gateway.platforms.discord as discord_mod

if os.getenv("DISABLE_DISCORD_FREE_RESPONSE_PATCH", "").lower() not in {"1", "true", "yes"}:
    _original = discord_mod.DiscordPlatform._handle_message

    async def _patched(self, message):
        return await _original(self, message)

    discord_mod.DiscordPlatform._handle_message = _patched
