from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import conftest  # noqa: F401
from discord_presence_plugin.collector import (
    CollectionError,
    fetch_codex_snapshot,
)


def usage_snapshot(*windows, provider="openai-codex", unavailable_reason=None):
    return SimpleNamespace(
        provider=provider,
        windows=tuple(windows),
        unavailable_reason=unavailable_reason,
    )


class HermesUsageCollectorTest(unittest.TestCase):
    def test_reads_hermes_usage_api_and_prefers_session_window(self):
        reset_at = datetime(2026, 8, 27, 2, 11, 9, tzinfo=timezone.utc)
        fetcher = Mock(
            return_value=usage_snapshot(
                SimpleNamespace(label="Weekly", used_percent=82.0, reset_at=reset_at),
                SimpleNamespace(label="Session", used_percent=7.4, reset_at=reset_at),
            )
        )

        snapshot = fetch_codex_snapshot(fetcher, now_fn=lambda: 456.0)

        fetcher.assert_called_once_with("openai-codex")
        self.assertEqual(snapshot.used_percent, 7)
        self.assertEqual(snapshot.remaining_percent, 93)
        self.assertEqual(snapshot.reset_at, int(reset_at.timestamp()))
        self.assertIsNone(snapshot.window_minutes)
        self.assertIsNone(snapshot.latest_date)
        self.assertIsNone(snapshot.latest_tokens)
        self.assertEqual(snapshot.fetched_at, 456.0)

    def test_falls_back_to_first_window_when_session_label_is_missing(self):
        reset_at = "2026-08-27T02:11:09Z"
        fetcher = Mock(
            return_value=usage_snapshot(
                SimpleNamespace(label="Current", used_percent=12.6, reset_at=reset_at),
            )
        )

        snapshot = fetch_codex_snapshot(fetcher)

        self.assertEqual(snapshot.used_percent, 13)
        self.assertEqual(snapshot.remaining_percent, 87)
        self.assertEqual(
            snapshot.reset_at,
            int(datetime(2026, 8, 27, 2, 11, 9, tzinfo=timezone.utc).timestamp()),
        )

    def test_clamps_percent_and_accepts_naive_reset_as_utc(self):
        high = fetch_codex_snapshot(
            Mock(
                return_value=usage_snapshot(
                    SimpleNamespace(
                        label="Session",
                        used_percent=170,
                        reset_at=datetime(2026, 8, 27, 2, 11, 9),
                    )
                )
            )
        )
        low = fetch_codex_snapshot(
            Mock(
                return_value=usage_snapshot(
                    SimpleNamespace(label="Session", used_percent=-10, reset_at="bad")
                )
            )
        )

        self.assertEqual(high.used_percent, 100)
        self.assertEqual(high.remaining_percent, 0)
        self.assertEqual(
            high.reset_at,
            int(datetime(2026, 8, 27, 2, 11, 9, tzinfo=timezone.utc).timestamp()),
        )
        self.assertEqual(low.used_percent, 0)
        self.assertEqual(low.remaining_percent, 100)
        self.assertIsNone(low.reset_at)

    def test_rejects_missing_or_invalid_usage_at_the_boundary(self):
        cases = (
            None,
            usage_snapshot(),
            usage_snapshot(SimpleNamespace(label="Session", used_percent=None)),
            usage_snapshot(SimpleNamespace(label="Session", used_percent=float("nan"))),
            usage_snapshot(
                SimpleNamespace(label="Session", used_percent=1),
                provider="anthropic",
            ),
            usage_snapshot(
                SimpleNamespace(label="Session", used_percent=1),
                unavailable_reason="not available",
            ),
        )

        for account_snapshot in cases:
            with self.subTest(account_snapshot=account_snapshot):
                with self.assertRaises(CollectionError):
                    fetch_codex_snapshot(Mock(return_value=account_snapshot))

    def test_hides_sensitive_exception_text(self):
        fetcher = Mock(side_effect=RuntimeError("credential=redacted-test-value"))

        with self.assertRaises(CollectionError) as caught:
            fetch_codex_snapshot(fetcher)

        message = str(caught.exception)
        self.assertIn("RuntimeError", message)
        self.assertNotIn("redacted-test-value", message)

    def test_handles_unavailable_hermes_import_without_crashing(self):
        from unittest.mock import patch

        with patch("discord_presence_plugin.collector.fetch_account_usage", None):
            with self.assertRaises(CollectionError):
                fetch_codex_snapshot()


if __name__ == "__main__":
    unittest.main()
