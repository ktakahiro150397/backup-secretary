from __future__ import annotations

import types
import unittest

import conftest  # noqa: F401
from discord_presence_plugin.plugin_entry import install_upstream_override


class ExistingDiscordAdapter:
    recovery_feature = True

    def __init__(self, config):
        self.config = config
        self._client = None

    async def connect(self, token):
        return True

    async def disconnect(self):
        return None


class FakeContext:
    def __init__(self):
        self.calls = []


class PluginEntryTest(unittest.TestCase):
    def test_wraps_current_upstream_adapter_and_reuses_registration(self):
        context = FakeContext()
        upstream = types.SimpleNamespace(DiscordAdapter=ExistingDiscordAdapter)

        def register(ctx):
            ctx.calls.append(upstream.DiscordAdapter)

        upstream.register = register

        installed = install_upstream_override(context, upstream_module=upstream)

        self.assertIs(upstream.DiscordAdapter, installed)
        self.assertTrue(issubclass(installed, ExistingDiscordAdapter))
        self.assertTrue(installed.recovery_feature)
        self.assertEqual(context.calls, [installed])

    def test_install_is_idempotent(self):
        context = FakeContext()
        upstream = types.SimpleNamespace(DiscordAdapter=ExistingDiscordAdapter)

        def register(ctx):
            ctx.calls.append(upstream.DiscordAdapter)

        upstream.register = register

        first = install_upstream_override(context, upstream_module=upstream)
        second = install_upstream_override(context, upstream_module=upstream)

        self.assertIs(first, second)
        self.assertEqual(context.calls, [first, first])


if __name__ == "__main__":
    unittest.main()
