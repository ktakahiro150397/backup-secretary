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
import re

if os.getenv("DISABLE_DISCORD_FREE_RESPONSE_PATCH", "").lower() in {"1", "true", "yes"}:
    # パッチ無効
    raise ImportError("patch disabled via env")

import gateway.platforms.discord as discord_mod

# --- 方法: ソースファイルを直接書き換える ---
filepath = discord_mod.__file__
with open(filepath, encoding="utf-8") as f:
    source = f.read()

old_line = "skip_thread = bool(channel_ids & no_thread_channels) or is_free_channel"
new_line = "skip_thread = bool(channel_ids & no_thread_channels)"

if old_line not in source:
    # 既にパッチ済みか、コード構造が変わっている
    if new_line in source:
        print("[patch] discord_free_response_thread: already patched, skipping")
    else:
        print("[patch] discord_free_response_thread: WARNING — target line not found, upstream may have changed")
    raise ImportError("already patched or target changed")

source = source.replace(old_line, new_line, 1)

# 念のためモジュールを再読み込みして新しいコードを反映
# （filepath の内容が変わるので次回 import からは新しいコードになる）
with open(filepath, "w", encoding="utf-8") as f:
    f.write(source)

# 既にロード済みのクラスメソッドを新しいコードで置き換える
import importlib
importlib.reload(discord_mod)
print("[patch] discord_free_response_thread: applied — skip_thread no longer includes is_free_channel")
