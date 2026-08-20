from __future__ import annotations

import unittest

import conftest  # noqa: F401 - installs the isolated package alias
from discord_presence_plugin.presence_config import PresenceConfig, load_presence_config


class PresenceConfigTest(unittest.TestCase):
    def test_defaults_are_safe_and_disabled(self):
        cfg = PresenceConfig.from_mapping({})

        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.mode, "rate_limit")
        self.assertEqual(cfg.refresh_seconds, 300)
        self.assertEqual(cfg.stale_after_seconds, 900)
        self.assertEqual(cfg.max_length, 120)
        self.assertEqual(cfg.timezone, "Asia/Tokyo")

    def test_unsafe_numeric_values_are_clamped(self):
        cfg = PresenceConfig.from_mapping(
            {
                "refresh_seconds": 1,
                "stale_after_seconds": 2,
                "max_length": 999,
            }
        )

        self.assertEqual(cfg.refresh_seconds, 60)
        self.assertEqual(cfg.stale_after_seconds, 60)
        self.assertEqual(cfg.max_length, 120)

    def test_unknown_mode_falls_back_without_crashing(self):
        cfg = PresenceConfig.from_mapping({"mode": "mystery"})

        self.assertEqual(cfg.mode, "rate_limit")
        self.assertEqual(cfg.validation_errors, ("unsupported mode: mystery",))

    def test_load_presence_config_reads_fresh_mapping_each_time(self):
        values = [
            {"discord": {"presence": {"enabled": False, "template": "first"}}},
            {"discord": {"presence": {"enabled": True, "template": "second"}}},
        ]

        first = load_presence_config(lambda: values.pop(0))
        second = load_presence_config(lambda: values.pop(0))

        self.assertFalse(first.enabled)
        self.assertEqual(first.template, "first")
        self.assertTrue(second.enabled)
        self.assertEqual(second.template, "second")

    def test_invalid_top_level_shape_falls_back_to_defaults(self):
        cfg = load_presence_config(lambda: {"discord": {"presence": "bad"}})

        self.assertEqual(cfg, PresenceConfig())


if __name__ == "__main__":
    unittest.main()
