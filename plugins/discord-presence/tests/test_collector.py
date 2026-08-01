from __future__ import annotations

import queue
import threading
from types import SimpleNamespace
import unittest

import conftest  # noqa: F401
from discord_presence_plugin.collector import (
    CollectionError,
    create_interruptible_codex_client,
    fetch_codex_snapshot,
)


class FakeClient:
    def __init__(self, responses=None, error=None):
        self.responses = responses or {}
        self.error = error
        self.calls = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    def initialize(self, **kwargs):
        self.calls.append(("initialize", kwargs))
        return {"ok": True}

    def request(self, method, timeout):
        self.calls.append((method, timeout))
        if self.error:
            raise self.error
        return self.responses[method]


class CodexCollectorTest(unittest.TestCase):
    def test_interruptible_client_close_wakes_pending_requests(self):
        class BaseClient:
            def __init__(self, codex_bin):
                self.codex_bin = codex_bin
                self._closed = False
                self._pending_lock = threading.Lock()
                self.pending = SimpleNamespace(queue=queue.Queue(maxsize=1))
                self._pending = {1: self.pending}
                self.close_timeout = None

            def close(self, timeout=3.0):
                self.close_timeout = timeout
                self._closed = True

        client = create_interruptible_codex_client(
            codex_bin="codex-test",
            base_class=BaseClient,
        )
        client.close(timeout=0.25)

        message = client.pending.queue.get_nowait()
        self.assertIn("error", message)
        self.assertEqual(client._pending, {})
        self.assertEqual(client.close_timeout, 0.25)

    def test_reads_only_usage_endpoints_and_closes_client(self):
        client = FakeClient(
            {
                "account/rateLimits/read": {
                    "rateLimits": {"primary": {"usedPercent": 25, "resetsAt": 123, "windowDurationMins": 300}}
                },
                "account/usage/read": {"dailyUsageBuckets": []},
            }
        )

        snapshot = fetch_codex_snapshot(lambda: client, now_fn=lambda: 456.0)

        self.assertEqual(
            [call[0] for call in client.calls],
            ["initialize", "account/rateLimits/read", "account/usage/read"],
        )
        self.assertTrue(client.closed)
        self.assertEqual(snapshot.used_percent, 25)
        self.assertEqual(snapshot.remaining_percent, 75)
        self.assertEqual(snapshot.fetched_at, 456.0)

    def test_prefers_requested_multi_bucket(self):
        client = FakeClient(
            {
                "account/rateLimits/read": {
                    "rateLimits": {"primary": {"usedPercent": 90}},
                    "rateLimitsByLimitId": {
                        "codex": {"primary": {"usedPercent": 12, "resetsAt": 987}}
                    },
                },
                "account/usage/read": {"dailyUsageBuckets": []},
            }
        )

        snapshot = fetch_codex_snapshot(lambda: client, bucket_id="codex")

        self.assertEqual(snapshot.used_percent, 12)
        self.assertEqual(snapshot.remaining_percent, 88)
        self.assertEqual(snapshot.reset_at, 987)

    def test_clamps_percent_and_handles_missing_primary(self):
        high = FakeClient(
            {
                "account/rateLimits/read": {"rateLimits": {"primary": {"usedPercent": 170}}},
                "account/usage/read": {"dailyUsageBuckets": []},
            }
        )
        missing = FakeClient(
            {
                "account/rateLimits/read": {"rateLimits": {}},
                "account/usage/read": {"dailyUsageBuckets": []},
            }
        )

        self.assertEqual(fetch_codex_snapshot(lambda: high).remaining_percent, 0)
        self.assertIsNone(fetch_codex_snapshot(lambda: missing).remaining_percent)

    def test_selects_latest_valid_daily_bucket(self):
        client = FakeClient(
            {
                "account/rateLimits/read": {"rateLimits": {"primary": {"usedPercent": 0}}},
                "account/usage/read": {
                    "dailyUsageBuckets": [
                        {"startDate": "2026-07-28", "tokens": 100},
                        {"startDate": "bad", "tokens": "oops"},
                        {"startDate": "2026-07-30", "tokens": 1234567},
                        {"startDate": "2026-07-29", "tokens": 200},
                    ]
                },
            }
        )

        snapshot = fetch_codex_snapshot(lambda: client)

        self.assertEqual(snapshot.latest_date, "2026-07-30")
        self.assertEqual(snapshot.latest_tokens, 1234567)

    def test_hides_sensitive_exception_text(self):
        client = FakeClient(error=RuntimeError("oauth_token=super-secret-value"))

        with self.assertRaises(CollectionError) as caught:
            fetch_codex_snapshot(lambda: client)

        message = str(caught.exception)
        self.assertIn("RuntimeError", message)
        self.assertNotIn("super-secret-value", message)
        self.assertTrue(client.closed)


if __name__ == "__main__":
    unittest.main()
