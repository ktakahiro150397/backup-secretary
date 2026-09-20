"""Run with HERMES_OTEL_TEST_PATH pointing at the patched plugin parent."""
import asyncio
from contextvars import ContextVar
import importlib
import json
import os
from pathlib import Path
import sys
import types
import unittest
import time

sys.path.insert(0, os.environ.get("HERMES_OTEL_TEST_PATH", "/opt/hermes/plugins"))
from hermes_otel import hooks, usage_contract as contract
from hermes_otel.plugin_config import HermesOtelConfig
from hermes_otel.tracer import HermesOTelPlugin
import hermes_otel.tracer as tracer_module
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

SECRET = "CANARY_PRIVATE_PROMPT_TOOL_ERROR_7ba9"
KEYS = ("PLATFORM", "USER_ID", "CHAT_ID", "CHAT_TYPE", "THREAD_ID", "PROFILE")


class UsageContractTest(unittest.TestCase):
    def setUp(self):
        self.old_context = sys.modules.get("gateway.session_context")
        module = types.ModuleType("gateway.session_context")
        module._VAR_MAP = {"HERMES_SESSION_" + k: ContextVar(k, default="") for k in KEYS}
        sys.modules["gateway.session_context"] = module
        self.context = module._VAR_MAP
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider(resource=Resource({"service.name": "backup-secretary-hermes",
            "service.instance.id": "synthetic", "host.name": SECRET}))
        self.provider.add_span_processor(contract.UsageProcessor(SimpleSpanProcessor(self.exporter)))
        self.plugin = HermesOTelPlugin(config=HermesOtelConfig(capture_sender_id=True,
            capture_previews=False, capture_conversation_history=False,
            capture_full_prompts=False, capture_full_responses=False, dashboard_live=False))
        self.plugin.tracer = self.provider.get_tracer("test")
        self.plugin._initialized = True
        tracer_module._tracer = self.plugin
        contract.install(hooks)
        contract._turns.clear()
        contract._children.clear()
        contract._inflight.clear()
        contract._retired.clear()
        contract._current.set(None)

    def tearDown(self):
        self.provider.shutdown()
        tracer_module._tracer = None
        if self.old_context is None:
            sys.modules.pop("gateway.session_context", None)
        else:
            sys.modules["gateway.session_context"] = self.old_context

    def begin(self, user="synthetic-a", thread="synthetic-thread-1", turn="t1", session="s1", platform="discord"):
        for key, value in dict(PLATFORM=platform, USER_ID=user, CHAT_ID=thread or "synthetic-channel",
                               CHAT_TYPE="thread" if thread else "dm", THREAD_ID=thread, PROFILE="main").items():
            self.context["HERMES_SESSION_" + key].set(value)
        hooks.on_pre_llm_call(session_id=session, task_id=turn, turn_id=turn,
            platform=platform, model="test-model", sender_id="stale-session-owner",
            user_message=SECRET, conversation_history=[], is_first_turn=False)

    def pre(self, turn="t1", session="s1", req="r1", retry=0):
        hooks.on_pre_api_request(task_id="shared-task", turn_id=turn, api_request_id=req,
            session_id=session, platform="discord", model="test-model", provider="openai-codex",
            base_url=SECRET, api_mode="responses", api_call_count=1, retry_count=retry,
            message_count=1, tool_count=0, approx_input_tokens=10, request_char_count=10,
            max_tokens=10, messages=[SECRET], system_prompt=SECRET)

    def post(self, turn="t1", session="s1", req="r1", usage=None):
        hooks.on_post_api_request(task_id="shared-task", turn_id=turn, api_request_id=req,
            session_id=session, platform="discord", model="test-model", provider="openai-codex",
            base_url=SECRET, api_mode="responses", api_call_count=1, api_duration=.1,
            finish_reason="stop", message_count=1, response_model="test-model",
            usage=usage, assistant_content_chars=10, assistant_tool_call_count=0,
            response_content=SECRET, response_tool_calls=[SECRET])

    def rows(self):
        spans = self.exporter.get_finished_spans()
        for span in spans:
            encoded = span.to_json()
            self.assertNotIn(SECRET, encoded)
            self.assertNotIn("stale-session-owner", encoded)
            self.assertEqual(span.name, "gen_ai.request")
            self.assertFalse(span.events)
            self.assertFalse(span.links)
        return [dict(s.attributes) for s in spans]

    def test_two_users_two_threads_interleaved_and_concurrent_same_session(self):
        async def scenario():
            async def request(user, thread, index):
                self.begin(user, thread, f"t{index}", "shared-session")
                await asyncio.sleep(0)
                self.pre(f"t{index}", "shared-session", f"r{index}")
                await asyncio.sleep(0)
                self.post(f"t{index}", "shared-session", f"r{index}",
                          {"input_tokens": 100 * index, "output_tokens": index,
                           "cache_read_tokens": 50, "reasoning_tokens": 1})
            await asyncio.gather(*(request(u, t, i) for i, (u, t) in enumerate(
                [(u, t) for u in ("synthetic-a", "synthetic-b")
                 for t in ("synthetic-thread-1", "synthetic-thread-2")], 1)))
        asyncio.run(scenario())
        rows = self.rows()
        self.assertEqual(len(rows), 4)
        self.assertEqual(sum(r["usage.tokens.total"] for r in rows), 1010)
        self.assertEqual([r["usage.user.id"] for r in rows],
                         ["discord:synthetic-a"]*2 + ["discord:synthetic-b"]*2)
        self.assertEqual(len({r["usage.thread.id"] for r in rows}), 2)

    def test_delegate_snapshot_survives_parent_next_turn(self):
        self.begin()
        hooks.on_subagent_start(parent_session_id="s1", child_session_id="child", child_role="worker")
        self.begin("synthetic-b", "synthetic-thread-2", "t2", "s1")
        self.begin("", "", "child-turn", "child", "subagent")
        self.pre("child-turn", "child", "child-request")
        self.post("child-turn", "child", "child-request", {"input_tokens": 11, "output_tokens": 7})
        row = self.rows()[0]
        self.assertEqual(row["usage.user.id"], "discord:synthetic-a")
        self.assertEqual(row["usage.thread.id"], "synthetic-thread-1")
        self.assertEqual(row["usage.parent.turn.id"], "t1")

    def test_error_retry_absent_usage_and_privacy(self):
        self.begin()
        self.pre()
        hooks.on_api_request_error(task_id="shared-task", turn_id="t1", api_request_id="r1",
            session_id="s1", model="test-model", provider="openai-codex", retry_count=0,
            error={"type": "provider_error", "message": SECRET}, reason=SECRET)
        self.pre(retry=1)
        self.post(usage={"input_tokens": 10, "output_tokens": 2, "cache_read_tokens": 9, "reasoning_tokens": 1})
        failed, success = self.rows()
        self.assertEqual(failed["usage.quality"], "missing")
        self.assertEqual(failed["usage.outcome"], "error")
        self.assertNotIn("usage.tokens.total", failed)
        self.assertEqual(success["usage.tokens.total"], 12)
        self.assertEqual(success["usage.retry"], 1)

    def test_resume_no_thread_system_and_missing_identity(self):
        for i, platform in enumerate(("discord", "cron", "discord")):
            self.begin("" if i == 2 else "synthetic-a", "", f"t{i}", "resumed", platform)
            self.pre(f"t{i}", "resumed", f"r{i}")
            self.post(f"t{i}", "resumed", f"r{i}", {"input_tokens": 0, "output_tokens": 0})
        rows = self.rows()
        self.assertEqual([r["usage.user.id"] for r in rows], ["discord:synthetic-a", "system", "unattributed"])
        self.assertTrue(all("usage.thread.id" not in r for r in rows))
        self.assertTrue(all(r["usage.tokens.total"] == 0 for r in rows))

    def test_environment_is_never_identity_source(self):
        os.environ["HERMES_SESSION_USER_ID"] = "other-user"
        try:
            self.begin("", "", "t1")
            self.pre()
            self.post(usage={"output_tokens": 3})
            row = self.rows()[0]
            self.assertEqual(row["usage.user.id"], "unattributed")
            self.assertEqual(row["usage.quality"], "partial")
            self.assertNotIn("usage.tokens.total", row)
        finally:
            os.environ.pop("HERMES_SESSION_USER_ID", None)

    def test_long_request_survives_session_orphan_sweep(self):
        self.begin()
        self.pre()
        self.plugin.register_turn("s1", time.perf_counter() - 7200)
        self.plugin.sweep_expired_turns()
        self.post(usage={"prompt_tokens": 100, "input_tokens": 20,
                         "cache_read_tokens": 80, "output_tokens": 7})
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["usage.tokens.total"], 107)

    def test_error_before_pre_and_reported_error_usage(self):
        self.begin()
        hooks.on_api_request_error(task_id="shared-task", turn_id="t1", api_request_id="early",
            session_id="s1", model="test-model", provider="openai-codex", retry_count=0,
            error={"type":"provider_error","message":SECRET},
            usage={"input_tokens":8,"output_tokens":2})
        row=self.rows()[0]
        self.assertEqual(row["usage.outcome"],"error")
        self.assertEqual(row["usage.tokens.total"],10)
        self.assertEqual(row["usage.user.id"],"discord:synthetic-a")

    def test_abandoned_request_state_is_bounded(self):
        self.begin()
        previous=contract._MAX_INFLIGHT
        try:
            contract._MAX_INFLIGHT=2
            for i in range(3): self.pre(req="bounded-"+str(i))
            row=self.rows()[0]
            self.assertEqual(row["usage.outcome"],"unknown")
            self.assertEqual(row["usage.quality"],"missing")
            self.assertEqual(len(contract._inflight),2)
            hooks.on_api_request_error(task_id="shared-task",turn_id="t1",api_request_id="bounded-0",
                session_id="s1",model="test-model",error={"message":SECRET})
            self.assertEqual(len(self.rows()),1)
        finally:
            contract._MAX_INFLIGHT=previous

    def test_trace_state_does_not_enter_export_queue(self):
        from opentelemetry.trace import NonRecordingSpan,SpanContext,TraceFlags,TraceState,set_span_in_context
        parent=NonRecordingSpan(SpanContext(123,456,False,TraceFlags(1),TraceState([("vendor",SECRET)])))
        span=self.provider.get_tracer("scope-canary").start_span("api.test",context=set_span_in_context(parent),
            attributes={"usage.contract":"hermes.request.v1"})
        span.end()
        self.rows()
        self.assertFalse(self.exporter.get_finished_spans()[0].context.trace_state)


if __name__ == "__main__":
    unittest.main()
