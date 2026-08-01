from __future__ import annotations

import asyncio
import threading
import unittest
from unittest.mock import AsyncMock, patch

import conftest  # noqa: F401
from discord_presence_plugin.adapter import (
    PresenceController,
    create_presence_adapter_class,
    fetch_snapshot_async,
)
from discord_presence_plugin.collector import CodexUsageSnapshot
from discord_presence_plugin.presence_config import PresenceConfig


class PresenceControllerTest(unittest.IsolatedAsyncioTestCase):
    async def test_async_fetch_cancellation_closes_client_and_joins_worker(self):
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()

        class FakeClient:
            closed = False

            def close(self, timeout=0.5):
                self.closed = True
                release.set()

        client = FakeClient()

        def blocking_fetch(*, client_factory, **_kwargs):
            self.assertIs(client_factory(), client)
            started.set()
            release.wait(timeout=2)
            finished.set()
            return CodexUsageSnapshot(remaining_percent=50)

        with (
            patch(
                "discord_presence_plugin.adapter.create_interruptible_codex_client",
                return_value=client,
                create=True,
            ),
            patch(
                "discord_presence_plugin.adapter.fetch_codex_snapshot",
                side_effect=blocking_fetch,
            ),
        ):
            task = asyncio.create_task(fetch_snapshot_async(PresenceConfig(enabled=True)))
            await asyncio.to_thread(started.wait, 1)
            task.cancel()
            try:
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertTrue(client.closed)
                self.assertTrue(finished.is_set())
            finally:
                release.set()
                await asyncio.to_thread(finished.wait, 1)

    async def test_updates_changed_text_and_suppresses_duplicate(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, template="Codex {remaining_percent}%")

        async def fetch(_cfg):
            return CodexUsageSnapshot(remaining_percent=73, fetched_at=10)

        controller = PresenceController(
            client,
            config_loader=lambda: cfg,
            snapshot_fetcher=fetch,
            activity_factory=lambda text: f"activity:{text}",
            clock=lambda: 10,
        )

        await controller.refresh_once()
        await controller.refresh_once()

        client.change_presence.assert_awaited_once_with(activity="activity:Codex 73%")

    async def test_keeps_previous_value_until_stale_then_uses_fallback(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(
            enabled=True,
            template="Codex {remaining_percent}%",
            stale_after_seconds=900,
            fallback_text="waiting",
        )
        now = [0.0]
        fail = [False]

        async def fetch(_cfg):
            if fail[0]:
                raise RuntimeError("secret response")
            return CodexUsageSnapshot(remaining_percent=73)

        controller = PresenceController(
            client,
            config_loader=lambda: cfg,
            snapshot_fetcher=fetch,
            activity_factory=lambda text: text,
            clock=lambda: now[0],
        )
        await controller.refresh_once()
        fail[0] = True
        now[0] = 100
        with self.assertLogs("discord_presence_plugin.adapter", level="WARNING"):
            await controller.refresh_once()
        self.assertEqual(client.change_presence.await_count, 1)

        now[0] = 901
        with self.assertLogs("discord_presence_plugin.adapter", level="WARNING"):
            await controller.refresh_once()
        self.assertEqual(client.change_presence.await_count, 2)
        client.change_presence.assert_awaited_with(activity="waiting")

    async def test_initial_failure_uses_fallback_and_does_not_leak_exception(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, fallback_text="waiting")

        async def fetch(_cfg):
            raise RuntimeError("oauth=super-secret")

        controller = PresenceController(
            client,
            config_loader=lambda: cfg,
            snapshot_fetcher=fetch,
            activity_factory=lambda text: text,
        )

        with self.assertLogs("discord_presence_plugin.adapter", level="WARNING") as logs:
            await controller.refresh_once()

        client.change_presence.assert_awaited_once_with(activity="waiting")
        self.assertNotIn("super-secret", "\n".join(logs.output))

    async def test_disabling_clears_activity_only_once(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = [PresenceConfig(enabled=True, mode="static", static_text="ready")]

        async def unused(_cfg):
            self.fail("collector should not run in static mode")

        controller = PresenceController(
            client,
            config_loader=lambda: cfg[0],
            snapshot_fetcher=unused,
            activity_factory=lambda text: text,
        )
        await controller.refresh_once()
        cfg[0] = PresenceConfig(enabled=False)
        await controller.refresh_once()
        await controller.refresh_once()

        self.assertEqual(client.change_presence.await_count, 2)
        client.change_presence.assert_awaited_with(activity=None)

    async def test_failed_discord_update_is_retried(self):
        change_presence = AsyncMock(side_effect=[RuntimeError("network"), None])
        client = type("Client", (), {"change_presence": change_presence})()
        cfg = PresenceConfig(enabled=True, mode="static", static_text="ready")
        controller = PresenceController(
            client,
            config_loader=lambda: cfg,
            snapshot_fetcher=AsyncMock(),
            activity_factory=lambda text: text,
        )

        with self.assertLogs("discord_presence_plugin.adapter", level="WARNING"):
            await controller.refresh_once()
        await controller.refresh_once()

        self.assertEqual(change_presence.await_count, 2)

    async def test_start_is_idempotent_and_stop_cancels_task(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, mode="static", static_text="ready", refresh_seconds=60)
        sleeping = asyncio.Event()

        async def sleep(_seconds):
            sleeping.set()
            await asyncio.Future()

        controller = PresenceController(
            client,
            config_loader=lambda: cfg,
            snapshot_fetcher=AsyncMock(),
            activity_factory=lambda text: text,
            sleep_fn=sleep,
        )

        first = controller.start()
        second = controller.start()
        await asyncio.wait_for(sleeping.wait(), timeout=1)

        self.assertIs(first, second)
        self.assertFalse(first.done())
        await controller.stop()
        self.assertTrue(first.done())
        self.assertIsNone(controller.task)

    async def test_stop_waits_for_inflight_fetch_to_finish_cleanly(self):
        client = type("Client", (), {"change_presence": AsyncMock()})()
        cfg = PresenceConfig(enabled=True, template="Codex {remaining_percent}%")
        started = asyncio.Event()
        release = asyncio.Event()
        cancelled = [False]

        async def fetch(_cfg):
            started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                cancelled[0] = True
                raise
            return CodexUsageSnapshot(remaining_percent=73)

        controller = PresenceController(
            client,
            config_loader=lambda: cfg,
            snapshot_fetcher=fetch,
            activity_factory=lambda text: text,
        )
        controller.start()
        await asyncio.wait_for(started.wait(), timeout=1)

        stop_task = asyncio.create_task(controller.stop())
        await asyncio.sleep(0)
        self.assertFalse(stop_task.done())

        release.set()
        await asyncio.wait_for(stop_task, timeout=1)
        self.assertFalse(cancelled[0])
        self.assertIsNone(controller.task)


class BaseAdapter:
    def __init__(self, config):
        self.config = config
        self._client = type("Client", (), {"change_presence": AsyncMock()})()
        self.connected = False
        self.is_reconnect = None
        self.disconnected = False

    async def connect(self, *, is_reconnect=False):
        self.connected = True
        self.is_reconnect = is_reconnect
        return True

    async def disconnect(self):
        self.disconnected = True


class PresenceAdapterLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def test_connect_starts_one_controller_and_disconnect_stops_it(self):
        cfg = PresenceConfig(enabled=True, mode="static", static_text="ready")
        adapter_cls = create_presence_adapter_class(
            BaseAdapter,
            config_loader=lambda: cfg,
            snapshot_fetcher=AsyncMock(),
            activity_factory=lambda text: text,
        )
        adapter = adapter_cls(config={})

        self.assertTrue(await adapter.connect(is_reconnect=True))
        self.assertTrue(adapter.is_reconnect)
        first_task = adapter._presence_controller.task
        self.assertTrue(await adapter.connect(is_reconnect=True))
        second_task = adapter._presence_controller.task

        self.assertIsNot(first_task, second_task)
        self.assertTrue(first_task.done())
        await adapter.disconnect()
        self.assertTrue(second_task.done())
        self.assertTrue(adapter.disconnected)

    async def test_disconnect_starts_base_cleanup_without_waiting_for_presence(self):
        adapter_cls = create_presence_adapter_class(BaseAdapter)
        adapter = adapter_cls(config={})
        stop_started = asyncio.Event()
        release_stop = asyncio.Event()

        class SlowController:
            async def stop(self):
                stop_started.set()
                await release_stop.wait()

        adapter._presence_controller = SlowController()
        disconnect_task = asyncio.create_task(adapter.disconnect())
        await asyncio.wait_for(stop_started.wait(), timeout=1)
        await asyncio.sleep(0)

        self.assertTrue(adapter.disconnected)
        self.assertFalse(disconnect_task.done())
        release_stop.set()
        await asyncio.wait_for(disconnect_task, timeout=1)


if __name__ == "__main__":
    unittest.main()
