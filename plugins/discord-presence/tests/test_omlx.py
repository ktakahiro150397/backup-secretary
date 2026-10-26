from __future__ import annotations

import asyncio
import io
import os
import unittest
from unittest.mock import AsyncMock, patch

import conftest  # noqa: F401
from discord_presence_plugin.adapter import PresenceController
from discord_presence_plugin.collector import CodexUsageSnapshot
from discord_presence_plugin.omlx import ActivityError, fetch_omlx_activity, render_activity
from discord_presence_plugin.presence_config import PresenceConfig


def activity(*models):
    return {"active_models": {"models": list(models)}}


class ActivityTest(unittest.TestCase):
    def test_idle_ignores_historical_stats(self):
        data = activity({"generating": [], "active_requests": 0})
        data["avg_generation_tps"] = 99.9
        self.assertEqual(render_activity(data), "idle")

    def test_native_rates_include_other_clients_and_models(self):
        self.assertEqual(render_activity(activity(
            {"id": "glm", "generating": [{"tokens_per_second": 75.14}]},
            {"id": "other-client", "generating": [{"tokens_per_second": 24.76}]},
        )), "99.9tok/s")

    def test_prefill_waiting_and_loading_are_busy_without_decode_rate(self):
        for row in ({"is_loading": True}, {"active_requests": 1}, {"waiting_requests": 1}):
            with self.subTest(row=row):
                self.assertEqual(render_activity(activity(row)), "0.0tok/s")

    def test_bad_or_missing_data_never_claims_idle(self):
        for data in ({}, {"active_models": {}}, activity({"generating": [{"tokens_per_second": float("nan")}] } )):
            with self.subTest(data=data), self.assertRaises(ActivityError):
                render_activity(data)

    def test_authentication_and_endpoint_without_logging_body(self):
        cfg = PresenceConfig(omlx_base_url="http://127.0.0.1:1234", omlx_key_env="TEST_OMLX_KEY")
        with patch.dict(os.environ, {"TEST_OMLX_KEY": "test-only-secret"}), patch(
            "discord_presence_plugin.omlx.urlopen", return_value=io.BytesIO(b'{"active_models":{"models":[]}}')
        ) as request:
            self.assertEqual(fetch_omlx_activity(cfg), "idle")
        self.assertEqual(request.call_args.args[0].full_url, "http://127.0.0.1:1234/admin/api/activity")
        self.assertEqual(request.call_args.args[0].get_header("Authorization"), "Bearer test-only-secret")
        self.assertEqual(request.call_args.kwargs["timeout"], 4)

    def test_failure_sanitizes_credentials_and_response(self):
        with patch.dict(os.environ, {"OMLX_API_KEY": "test-only-secret"}), patch(
            "discord_presence_plugin.omlx.urlopen", side_effect=RuntimeError("test-only-secret response")
        ), self.assertRaises(ActivityError) as caught:
            fetch_omlx_activity(PresenceConfig(omlx_base_url="http://127.0.0.1"))
        self.assertEqual(str(caught.exception), "oMLX activity unavailable")


class IndependentRefreshTest(unittest.IsolatedAsyncioTestCase):
    async def test_omlx_changes_without_new_codex_call_or_bot_turn(self):
        now = [0.0]
        client = type("Client", (), {"change_presence": AsyncMock()})()
        usage = AsyncMock(return_value=CodexUsageSnapshot(remaining_percent=73))
        rates = AsyncMock(side_effect=["idle", "99.9tok/s", "idle"])
        cfg = PresenceConfig(enabled=True, template="Codex残量 {remaining_percent}%", refresh_seconds=900,
                             omlx_base_url="http://127.0.0.1")
        controller = PresenceController(client, config_loader=lambda: cfg, snapshot_fetcher=usage,
            activity_fetcher=rates, activity_factory=lambda text: text, clock=lambda: now[0])
        for instant in (0, 15, 30):
            now[0] = instant
            await controller.refresh_once()
        self.assertEqual([c.kwargs["activity"] for c in client.change_presence.await_args_list],
                         ["idle｜Codex残量 73%", "99.9tok/s｜Codex残量 73%", "idle｜Codex残量 73%"])
        usage.assert_awaited_once()
        self.assertEqual(rates.await_count, 3)

    async def test_codex_failure_does_not_hide_live_speed(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, fallback_text="waiting", omlx_base_url="http://127.0.0.1")
        controller = PresenceController(client, config_loader=lambda: cfg,
            snapshot_fetcher=AsyncMock(side_effect=RuntimeError("private")),
            activity_fetcher=AsyncMock(return_value="99.9tok/s"), activity_factory=lambda text: text)
        with self.assertLogs("discord_presence_plugin.adapter", level="WARNING"):
            await controller.refresh_once()
        client.change_presence.assert_awaited_once_with(activity="99.9tok/s｜waiting")

    async def test_omlx_failure_never_repeats_stale_speed(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, mode="static", static_text="ready", omlx_base_url="http://127.0.0.1")
        now = [0.0]
        controller = PresenceController(client, config_loader=lambda: cfg, clock=lambda: now[0],
            activity_fetcher=AsyncMock(side_effect=["99.9tok/s", ActivityError("offline")]),
            activity_factory=lambda text: text)
        await controller.refresh_once()
        now[0] = 5
        with self.assertLogs("discord_presence_plugin.adapter", level="WARNING"):
            await controller.refresh_once()
        client.change_presence.assert_awaited_with(activity="oMLX取得待ち｜ready")

    async def test_usage_refresh_respects_interval_and_expires_stale_data(self):
        now = [0.0]
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, template="{remaining_percent}%", fallback_text="waiting",
            refresh_seconds=60, stale_after_seconds=120, omlx_base_url="http://127.0.0.1")
        usage = AsyncMock(side_effect=[CodexUsageSnapshot(remaining_percent=73), RuntimeError(), RuntimeError()])
        controller = PresenceController(client, config_loader=lambda: cfg, snapshot_fetcher=usage,
            activity_fetcher=AsyncMock(return_value="idle"), activity_factory=lambda text: text, clock=lambda: now[0])
        await controller.refresh_once()
        for instant in (60, 121):
            now[0] = instant
            with self.assertLogs("discord_presence_plugin.adapter", level="WARNING"):
                await controller.refresh_once()
        self.assertEqual(usage.await_count, 3)
        client.change_presence.assert_awaited_with(activity="idle｜waiting")

    async def test_poll_loop_uses_short_interval(self):
        intervals = []
        sleeping = asyncio.Event()
        async def sleep(seconds):
            intervals.append(seconds)
            sleeping.set()
            await asyncio.Future()
        cfg = PresenceConfig(enabled=True, mode="static", omlx_base_url="http://127.0.0.1", refresh_seconds=900)
        controller = PresenceController(type("Client", (), {"change_presence": AsyncMock()})(),
            config_loader=lambda: cfg, activity_fetcher=AsyncMock(return_value="idle"),
            activity_factory=lambda text: text, sleep_fn=sleep)
        controller.start()
        await asyncio.wait_for(sleeping.wait(), 1)
        await controller.stop()
        self.assertEqual(intervals, [1])

    async def test_native_polling_continues_while_discord_updates_are_throttled(self):
        now = [0.0]
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, mode="static", static_text="ready", omlx_base_url="http://127.0.0.1")
        rates = AsyncMock(side_effect=[f"{n}.0tok/s" for n in range(7)])
        controller = PresenceController(client, config_loader=lambda: cfg, clock=lambda: now[0],
            activity_fetcher=rates, activity_factory=lambda text: text)
        for instant in range(7):
            now[0] = instant
            await controller.refresh_once()
        self.assertEqual(rates.await_count, 7)
        self.assertEqual([c.kwargs["activity"] for c in client.change_presence.await_args_list],
                         ["0.0tok/s｜ready", "5.0tok/s｜ready"])


if __name__ == "__main__":
    unittest.main()
