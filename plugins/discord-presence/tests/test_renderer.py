from __future__ import annotations

import unittest
from datetime import datetime, timezone

import conftest  # noqa: F401
from discord_presence_plugin.collector import CodexUsageSnapshot
from discord_presence_plugin.presence_config import PresenceConfig
from discord_presence_plugin.renderer import RenderError, build_custom_activity, format_tokens, render_presence


class PresenceRendererTest(unittest.TestCase):
    def test_renders_rate_limit_and_reset_date_time_in_jst(self):
        reset_at = int(datetime(2026, 7, 30, 9, 0, tzinfo=timezone.utc).timestamp())
        snapshot = CodexUsageSnapshot(
            used_percent=27,
            remaining_percent=73,
            reset_at=reset_at,
            window_minutes=300,
        )
        cfg = PresenceConfig(enabled=True)

        text = render_presence(snapshot, cfg)

        self.assertEqual(text, "Codex残量 73%｜次回リセット 07/30 18:00")

    def test_formats_compact_token_counts(self):
        self.assertEqual(format_tokens(999), "999")
        self.assertEqual(format_tokens(1_200), "1.2K")
        self.assertEqual(format_tokens(1_234_567), "1.2M")
        self.assertEqual(format_tokens(2_000_000_000), "2B")

    def test_daily_token_placeholders_are_whitelisted(self):
        snapshot = CodexUsageSnapshot(latest_date="2026-07-30", latest_tokens=1_234_567)
        cfg = PresenceConfig(
            enabled=True,
            mode="daily_tokens",
            template="Codex {latest_date} {latest_tokens_short} tok",
        )

        text = render_presence(snapshot, cfg)

        self.assertEqual(text, "Codex 2026-07-30 1.2M tok")

    def test_unknown_placeholder_fails_without_echoing_snapshot_metadata(self):
        snapshot = CodexUsageSnapshot(remaining_percent=73)
        cfg = PresenceConfig(enabled=True, template="{account_id}")

        with self.assertRaises(RenderError) as caught:
            render_presence(snapshot, cfg)

        self.assertEqual(str(caught.exception), "unsupported template placeholder")

    def test_truncates_without_exceeding_configured_length(self):
        snapshot = CodexUsageSnapshot(remaining_percent=73)
        cfg = PresenceConfig(enabled=True, template="x" * 200, max_length=20)

        self.assertEqual(render_presence(snapshot, cfg), "x" * 20)

    def test_static_mode_does_not_require_codex_values(self):
        cfg = PresenceConfig(enabled=True, mode="static", static_text="Hermes ready")

        self.assertEqual(render_presence(None, cfg), "Hermes ready")

    def test_builds_discord_custom_activity_type_four(self):
        activity = build_custom_activity("Codex残量 73%")

        payload = activity.to_dict()
        self.assertEqual(payload["type"], 4)
        self.assertEqual(payload["state"], "Codex残量 73%")
        self.assertEqual(payload["name"], "Custom Status")


if __name__ == "__main__":
    unittest.main()
