from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .collector import (
    CodexUsageSnapshot,
    create_interruptible_codex_client,
    fetch_codex_snapshot,
)
from .presence_config import PresenceConfig, load_presence_config
from .renderer import build_custom_activity, render_presence


logger = logging.getLogger(__name__)

ConfigLoader = Callable[[], PresenceConfig]
SnapshotFetcher = Callable[[PresenceConfig], Awaitable[CodexUsageSnapshot]]
ActivityFactory = Callable[[str], Any]


async def fetch_snapshot_async(config: PresenceConfig) -> CodexUsageSnapshot:
    client = create_interruptible_codex_client()
    worker = asyncio.create_task(
        asyncio.to_thread(
            fetch_codex_snapshot,
            client_factory=lambda: client,
            bucket_id=config.bucket_id,
            timeout=15.0,
        )
    )
    try:
        return await asyncio.wait_for(asyncio.shield(worker), timeout=20.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        # asyncio.to_thread cancellation does not stop its worker. This client
        # close kills the Codex child and wakes the pending JSON-RPC queue, then
        # we join the worker before allowing adapter shutdown to complete.
        client.close(timeout=0.5)
        try:
            await asyncio.wait_for(asyncio.shield(worker), timeout=1.0)
        except (Exception, asyncio.CancelledError):
            if not worker.done():
                worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
        raise


class PresenceController:
    def __init__(
        self,
        client: Any,
        *,
        config_loader: ConfigLoader = load_presence_config,
        snapshot_fetcher: SnapshotFetcher = fetch_snapshot_async,
        activity_factory: ActivityFactory = build_custom_activity,
        clock: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._config_loader = config_loader
        self._snapshot_fetcher = snapshot_fetcher
        self._activity_factory = activity_factory
        self._clock = clock
        self._sleep = sleep_fn
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._last_text: str | None = None
        self._last_success_at: float | None = None
        self._has_published = False

    @property
    def task(self) -> asyncio.Task[None] | None:
        return self._task

    def _load_config(self) -> PresenceConfig:
        try:
            config = self._config_loader()
        except Exception as exc:
            logger.warning("Discord presence config read failed (%s)", type(exc).__name__)
            return PresenceConfig()
        return config if isinstance(config, PresenceConfig) else PresenceConfig()

    async def _publish(self, text: str | None) -> bool:
        if self._has_published and text == self._last_text:
            return True
        try:
            activity = None if text is None else self._activity_factory(text)
            await self._client.change_presence(activity=activity)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Discord presence update failed (%s)", type(exc).__name__)
            return False
        self._last_text = text
        self._has_published = True
        return True

    async def _handle_failure(self, config: PresenceConfig) -> None:
        now = self._clock()
        if self._last_success_at is not None:
            age = max(0.0, now - self._last_success_at)
            if age <= config.stale_after_seconds:
                return
        await self._publish(config.fallback_text[: config.max_length])

    async def refresh_once(self) -> PresenceConfig:
        config = self._load_config()
        if not config.enabled:
            if self._has_published and self._last_text is not None:
                await self._publish(None)
            return config

        try:
            snapshot = None
            if config.mode != "static":
                snapshot = await self._snapshot_fetcher(config)
            text = render_presence(snapshot, config)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Discord presence data unavailable (%s)", type(exc).__name__)
            await self._handle_failure(config)
            return config

        if await self._publish(text):
            self._last_success_at = self._clock()
        return config

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            config = await self.refresh_once()
            if self._stop_event.is_set():
                break
            sleep_task = asyncio.create_task(self._sleep(config.refresh_seconds))
            stop_task = asyncio.create_task(self._stop_event.wait())
            done, pending = await asyncio.wait(
                {sleep_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for pending_task in pending:
                pending_task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for completed_task in done:
                completed_task.result()

    def start(self) -> asyncio.Task[None]:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run(), name="discord-presence-refresh")
        return self._task

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        self._stop_event.set()
        try:
            # GatewayRunner gives each adapter a five-second disconnect budget.
            # Keep our own grace period below that budget; disconnect() runs this
            # concurrently with the upstream Discord cleanup.
            await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("Discord presence task did not stop within timeout")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        except asyncio.CancelledError:
            task.cancel()
            raise


def create_presence_adapter_class(
    base_adapter_class: type,
    *,
    config_loader: ConfigLoader = load_presence_config,
    snapshot_fetcher: SnapshotFetcher = fetch_snapshot_async,
    activity_factory: ActivityFactory = build_custom_activity,
) -> type:
    class PresenceDiscordAdapter(base_adapter_class):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._presence_controller: PresenceController | None = None

        async def _stop_presence_controller(self) -> None:
            controller = self._presence_controller
            self._presence_controller = None
            if controller is not None:
                await controller.stop()

        async def connect(self, *, is_reconnect: bool = False) -> bool:
            await self._stop_presence_controller()
            connected = await super().connect(is_reconnect=is_reconnect)
            if connected and getattr(self, "_client", None) is not None:
                self._presence_controller = PresenceController(
                    self._client,
                    config_loader=config_loader,
                    snapshot_fetcher=snapshot_fetcher,
                    activity_factory=activity_factory,
                )
                self._presence_controller.start()
            return connected

        async def disconnect(self) -> None:
            controller = self._presence_controller
            self._presence_controller = None
            if controller is None:
                await super().disconnect()
                return

            # Start upstream Discord cleanup immediately instead of spending
            # its outer gateway timeout budget waiting for the Codex read.
            results = await asyncio.gather(
                controller.stop(),
                super().disconnect(),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, BaseException):
                    raise result

    PresenceDiscordAdapter.__name__ = "PresenceDiscordAdapter"
    PresenceDiscordAdapter.__qualname__ = "PresenceDiscordAdapter"
    return PresenceDiscordAdapter
