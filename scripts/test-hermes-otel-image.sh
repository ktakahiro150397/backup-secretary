#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
image=${1:-backup-secretary/hermes-agent:local}

docker run --rm -i \
  --network local-observability-net \
  --tmpfs /opt/testhome:rw,nosuid,size=32m,uid=1000,gid=1000,mode=0700 \
  -e HOME=/opt/testhome \
  -e HERMES_HOME=/opt/testhome \
  -v "${repo_dir}/observability/hermes-otel/main.yaml:/run/main.yaml:ro" \
  -v "${repo_dir}/observability/hermes-otel/owashota.yaml:/run/owashota.yaml:ro" \
  --entrypoint bash \
  "${image}" -s <<'CONTAINER_SCRIPT'
set -euo pipefail
mkdir -p "${HOME}/.hermes/plugins/hermes_otel"
cp /run/main.yaml "${HOME}/.hermes/plugins/hermes_otel/config.yaml"

python - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, "/opt/hermes/plugins")
from hermes_otel.plugin_config import load_config

hooks_source = Path("/opt/hermes/plugins/hermes_otel/hooks.py").read_text()
for blocked_key in (
    "hermes.tool.command",
    "hermes.tool.target",
    "hermes.turn.tool_commands",
    "hermes.turn.tool_targets",
    "error.message",
):
    assert f'"{blocked_key}"' not in hooks_source

for name in ("main", "owashota"):
    cfg = load_config(path=Path(f"/run/{name}.yaml"))
    attrs = cfg.resource_attributes
    assert attrs["service.name"] == "backup-secretary-hermes"
    assert attrs["service.namespace"] == "backup-secretary"
    assert attrs["service.instance.id"] == name
    assert cfg.capture_previews is False
    assert cfg.capture_conversation_history is False
    assert cfg.capture_full_prompts is False
    assert cfg.capture_full_responses is False
    assert cfg.capture_sender_id is True
    assert cfg.capture_logs is False
    assert cfg.force_flush_on_session_end is False
    assert cfg.backends
    assert cfg.backends[0].endpoint == "http://otel-router:4318/v1/traces"
print("CONFIG_ASSERTIONS_OK")
PY

python - <<'PY'
import sys

sys.path.insert(0, "/opt/hermes/plugins")

from hermes_otel.hooks import (
    on_post_api_request,
    on_post_llm_call,
    on_pre_api_request,
    on_pre_llm_call,
    on_session_end,
    on_session_start,
    on_subagent_start,
    on_subagent_stop,
)
from hermes_otel.plugin_config import HermesOtelConfig
from hermes_otel.tracer import HermesOTelPlugin
import hermes_otel.tracer as tracer_module
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


exporter = InMemorySpanExporter()
provider = TracerProvider(resource=Resource.create({"service.name": "synthetic-test"}))
provider.add_span_processor(SimpleSpanProcessor(exporter))
plugin = HermesOTelPlugin(
    config=HermesOtelConfig(
        capture_sender_id=True,
        capture_previews=False,
        capture_conversation_history=False,
        capture_full_prompts=False,
        capture_full_responses=False,
    )
)
plugin.tracer = provider.get_tracer("subagent-sender-test")
plugin._initialized = True
tracer_module._tracer = plugin

try:
    on_session_start(session_id="parent", model="test-model", platform="discord")
    on_pre_llm_call(
        session_id="parent",
        user_message="synthetic",
        conversation_history=[],
        is_first_turn=True,
        model="test-model",
        platform="discord",
        sender_id="synthetic-user",
    )
    on_subagent_start(
        parent_session_id="parent",
        child_session_id="child",
        child_role="synthetic-role",
    )
    on_session_start(session_id="child", model="test-model", platform="subagent")
    on_pre_llm_call(
        session_id="child",
        user_message="synthetic child input",
        conversation_history=[],
        is_first_turn=True,
        model="test-model",
        platform="subagent",
    )
    on_pre_api_request(
        task_id="child-task",
        session_id="child",
        platform="subagent",
        model="test-model",
        provider="synthetic-provider",
        base_url="https://invalid.example",
        api_mode="chat",
        api_call_count=1,
        message_count=1,
        tool_count=0,
        approx_input_tokens=11,
        request_char_count=21,
        max_tokens=100,
    )
    on_post_api_request(
        task_id="child-task",
        session_id="child",
        platform="subagent",
        model="test-model",
        provider="synthetic-provider",
        base_url="https://invalid.example",
        api_mode="chat",
        api_call_count=1,
        api_duration=0.01,
        finish_reason="stop",
        message_count=1,
        response_model="test-model",
        usage={
            "input_tokens": 11,
            "output_tokens": 7,
            "total_tokens": 18,
            "cache_read_tokens": 3,
            "reasoning_tokens": 2,
        },
        assistant_content_chars=22,
        assistant_tool_call_count=0,
    )
    on_post_llm_call(
        session_id="child",
        user_message="synthetic child input",
        assistant_response="synthetic child output",
        conversation_history=[],
        model="test-model",
        platform="subagent",
    )
    on_session_end(
        session_id="child",
        completed=True,
        interrupted=False,
        model="test-model",
        platform="subagent",
    )
    on_subagent_stop(
        parent_session_id="parent",
        child_session_id="child",
        child_role="synthetic-role",
        child_status="completed",
    )
    on_post_llm_call(
        session_id="parent",
        user_message="synthetic",
        assistant_response="synthetic",
        conversation_history=[],
        model="test-model",
        platform="discord",
    )
    on_session_end(
        session_id="parent",
        completed=True,
        interrupted=False,
        model="test-model",
        platform="discord",
    )

    finished_spans = exporter.get_finished_spans()
    child_spans = [
        span
        for span in finished_spans
        if dict(span.attributes).get("session.id") == "child"
    ]
    assert {span.name for span in child_spans} == {
        "agent",
        "api.test-model",
        "llm.test-model",
    }
    for span in child_spans:
        attributes = dict(span.attributes)
        assert attributes["hermes.sender.id"] == "synthetic-user"
        assert attributes["user.id"] == "discord:synthetic-user"
        assert attributes.get("hermes.sender.id") != "None"
        assert attributes.get("user.id") != "subagent:None"
        for blocked_key in (
            "input.value",
            "output.value",
            "gen_ai.input.messages",
            "gen_ai.output.messages",
            "llm.input_messages",
            "llm.output.content",
        ):
            assert blocked_key not in attributes

    child_agent = next(span for span in child_spans if span.name == "agent")
    child_attributes = dict(child_agent.attributes)
    assert child_attributes["gen_ai.usage.input_tokens"] == 11
    assert child_attributes["gen_ai.usage.output_tokens"] == 7
    assert child_attributes["gen_ai.usage.total_tokens"] == 18
    assert child_attributes["gen_ai.usage.cache_read.input_tokens"] == 3
    assert child_attributes["gen_ai.usage.reasoning.output_tokens"] == 2

    delegation = next(span for span in finished_spans if span.name == "subagent.synthetic-role")
    delegation_attributes = dict(delegation.attributes)
    assert delegation_attributes["hermes.sender.id"] == "synthetic-user"
    assert delegation_attributes["user.id"] == "discord:synthetic-user"
    print("SUBAGENT_SENDER_INHERITANCE_OK")
finally:
    provider.shutdown()
    tracer_module._tracer = None
PY

hermes plugins enable --no-allow-tool-override hermes_otel >/dev/null
python - <<'PY'
from hermes_cli.plugins import get_plugin_manager

manager = get_plugin_manager()
manager.discover_and_load(force=True)
matches = [
    loaded for key, loaded in manager._plugins.items()
    if key == "hermes_otel" or loaded.manifest.name == "hermes_otel"
]
assert matches
assert matches[0].enabled is True
assert not matches[0].error
print("PLUGIN_LOAD_OK")
PY

hermes plugins list --enabled --json | python -c '
import json
import sys

data = json.load(sys.stdin)
rows = data if isinstance(data, list) else data.get("plugins", [])
matches = [
    row for row in rows
    if row.get("name") == "hermes_otel" or row.get("key") == "hermes_otel"
]
assert matches
assert matches[0].get("status") == "enabled"
print("PLUGIN_ENABLED_OK")
'
CONTAINER_SCRIPT
