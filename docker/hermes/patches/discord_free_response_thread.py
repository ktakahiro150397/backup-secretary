# docker/hermes/patches/discord_free_response_thread.py
"""
一時モンキーパッチ（PR #26074 相当）

free_response_channels でも auto_thread を効かせるよう、
skip_thread の計算から is_free_channel を除去する。

修正対象（discord.py L4479）:
  skip_thread = bool(channel_ids & no_thread_channels) or is_free_channel
  → skip_thread = bool(channel_ids & no_thread_channels)

次回 Hermes アプデで公式修正が入ったら、このファイルごと削除。
"""
import os
import textwrap
import inspect
import sys

if os.getenv("DISABLE_DISCORD_FREE_RESPONSE_PATCH", "").lower() in {"1", "true", "yes"}:
    raise ImportError("patch disabled via env")

import gateway.platforms.discord as discord_mod

# ── ランタイムモンキーパッチ ──
# ファイル書き込み権限がない環境でも動くよう、in-memory でメソッドを差し替える

original = discord_mod.DiscordAdapter._handle_message
source = inspect.getsource(original)
source = textwrap.dedent(source)

old_line = "skip_thread = bool(channel_ids & no_thread_channels) or is_free_channel"
new_line = "skip_thread = bool(channel_ids & no_thread_channels)"

if old_line not in source:
    if new_line in source:
        print("[patch] discord_free_response_thread: already patched, skipping")
    else:
        print("[patch] discord_free_response_thread: WARNING — target line not found, upstream may have changed. source snippet:")
        for i, line in enumerate(source.split("\n")[40:50]):
            print(f"  {i+41}| {line}")
    raise ImportError("already patched or target changed")

source = source.replace(old_line, new_line, 1)

# exec して新しい関数を取得
# （関数内で参照しているモジュールレベルの名前は discord_mod の __dict__ から拾う）
namespace = dict(discord_mod.__dict__)
exec(source, namespace)
patched = namespace["_handle_message"]

# 元の関数の属性（__module__ など）を引き継ぐ
patched.__module__ = original.__module__
patched.__qualname__ = original.__qualname__

# 差し替え
discord_mod.DiscordAdapter._handle_message = patched
print("[patch] discord_free_response_thread: applied — skip_thread no longer includes is_free_channel")
