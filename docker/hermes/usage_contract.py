"""Opt-in request accounting for the pinned hermes-otel plugin.

Identity comes from gateway ContextVars, never process environment or prompts.
The existing plugin still owns hook registration, spans and asynchronous export.
"""
from collections import OrderedDict
from contextvars import ContextVar
from functools import wraps
import inspect
import re
from threading import RLock
import time
from uuid import uuid4
from opentelemetry.sdk.trace import SpanProcessor

_current = ContextVar("hermes_usage_turn", default=None)
_lock = RLock()
_turns = OrderedDict()
_children = OrderedDict()
_inflight = OrderedDict()
_retired = OrderedDict()
_MAX_CONTEXTS = 8192
_MAX_INFLIGHT = 4096
_REQUEST_TTL = 24 * 3600
_ID = re.compile(r"^[A-Za-z0-9_.:@-]{1,200}$")


def identifier(value):
    value = str(value) if value is not None else ""
    return value if _ID.fullmatch(value) else ""


def gateway_context():
    # get_session_env deliberately falls back to os.environ. Do not use it:
    # that can be another concurrent turn's identity. Fail closed on old hosts.
    try:
        from gateway.session_context import _VAR_MAP
        return {k: v.get() for k, v in _VAR_MAP.items()
                if isinstance(v.get(), (str, bool))}
    except (ImportError, AttributeError):
        return {}


def remember(store, key, value):
    with _lock:
        store[key] = value.copy()
        store.move_to_end(key)
        while len(store) > _MAX_CONTEXTS:
            store.popitem(last=False)


def turn_key(data):
    return identifier(data.get("turn_id") or data.get("task_id"))


def begin_turn(data):
    ctx = gateway_context()
    session = identifier(data.get("session_id"))
    key = turn_key(data) or str(uuid4())
    platform = identifier(data.get("platform"))
    with _lock:
        inherited = _children.get(session, {}).copy()
    attrs = {
        "usage.contract": "hermes.request.v1",
        "usage.turn.id": key,
        "usage.session.id": session,
        "usage.transport": platform or "unknown",
        "usage.attribution": "unattributed",
        "usage.user.id": "unattributed",
        "usage.thread.kind": "none",
    }
    if platform == "subagent" and inherited:
        attrs.update(inherited)
        attrs.update({"usage.turn.id": key, "usage.session.id": session,
                      "usage.parent.turn.id": inherited.get("usage.turn.id", ""),
                      "usage.parent.session.id": inherited.get("usage.session.id", "")})
    elif platform in {"cron", "self-improvement"} or ctx.get("HERMES_CRON_SESSION") in {True, "1", "true"}:
        attrs.update({"usage.user.id": "system", "usage.attribution": "system"})
    elif platform == "discord":
        sender = identifier(ctx.get("HERMES_SESSION_USER_ID"))
        # A gateway-bound sender is authoritative even if a reused agent's
        # constructor user_id (and therefore the old hook sender_id) is stale.
        if ctx.get("HERMES_SESSION_PLATFORM") == "discord" and sender:
            attrs.update({"usage.user.id": "discord:" + sender,
                          "usage.attribution": "gateway"})
            for suffix, field in (("CHAT_ID", "channel.id"), ("THREAD_ID", "thread.id"),
                                  ("PROFILE", "profile")):
                value = identifier(ctx.get("HERMES_SESSION_" + suffix))
                if value:
                    attrs["usage." + field] = value
            if attrs.get("usage.thread.id"):
                attrs["usage.thread.kind"] = "thread"
            elif ctx.get("HERMES_SESSION_CHAT_TYPE") == "thread" and attrs.get("usage.channel.id"):
                # Discord adapter uses the thread's channel ID as chat_id.
                attrs["usage.thread.id"] = attrs["usage.channel.id"]
                attrs["usage.thread.kind"] = "thread"
    remember(_turns, key, attrs)
    _current.set(attrs.copy())
    return attrs


def numeric_usage(usage):
    """Preserve absent buckets; cache/reasoning are subsets, not additions."""
    usage = usage if isinstance(usage, dict) else {}
    fields = {
        "input": ("prompt_tokens", "input_tokens"),
        "output": ("output_tokens", "completion_tokens"),
        "cache_read": ("cache_read_tokens",),
        "cache_write": ("cache_write_tokens", "cache_creation_tokens"),
        "reasoning": ("reasoning_tokens",),
    }
    out = {}
    for target, keys in fields.items():
        for key in keys:
            value = usage.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2**63 - 1:
                out["usage.tokens." + target] = value
                break
    if "usage.tokens.input" in out and "usage.tokens.output" in out:
        out["usage.tokens.total"] = out["usage.tokens.input"] + out["usage.tokens.output"]
        out["usage.quality"] = "reported"
    else:
        out["usage.quality"] = "partial" if out else "missing"
    return out


def install(hooks):
    if getattr(hooks, "_request_usage_installed", False):
        return
    hooks._request_usage_installed = True

    def wrap(name):
        original = getattr(hooks, name)
        signature = inspect.signature(original)

        @wraps(original)
        def callback(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            data = dict(bound.arguments)
            data.update(data.pop("kwargs", {}))
            tracer = hooks.get_tracer()
            fallback_error = False
            if name == "on_pre_llm_call":
                begin_turn(data)
            elif name == "on_subagent_start":
                parent = _current.get()
                if parent and parent.get("usage.session.id") == data.get("parent_session_id"):
                    remember(_children, data.get("child_session_id"), parent)
            elif name in {"on_pre_api_request", "on_post_api_request", "on_api_request_error"}:
                request = identifier(data.get("api_request_id"))
                if request:
                    # Upstream keys by task_id, which collides across requests
                    # and concurrent turns. The native request ID is turn-local.
                    data["task_id"] = request
                key = "api:" + str(data.get("task_id"))
                if name == "on_pre_api_request":
                    # Interrupted requests may never receive a terminal hook.
                    # Bound accounting state independently of the root TTL.
                    with _lock:
                        now = time.monotonic()
                        while _inflight:
                            old_key, (old_tracer, opened) = next(iter(_inflight.items()))
                            if len(_inflight) < _MAX_INFLIGHT and now-opened < _REQUEST_TTL:
                                break
                            _inflight.pop(old_key)
                            remember(_retired, old_key, {})
                            old_tracer.end_span(old_key)
                        _retired.pop(key, None)
                        _inflight[key] = (tracer, now)
                if name != "on_pre_api_request":
                    with _lock:
                        _inflight.pop(key, None)
                    span = tracer.spans.get_span(key)
                    fallback_error = name == "on_api_request_error" and span is None and key not in _retired
                    if span is not None:
                        values = numeric_usage(data.get("usage"))
                        values["usage.outcome"] = "error" if name == "on_api_request_error" else "ok"
                        span.set_attributes(values)
            result = original(**data)
            if fallback_error:
                # Upstream's fallback ended before our processor saw a contract.
                # Emit one content-free error fact; do not invent token usage.
                with _lock:
                    attrs = _turns.get(turn_key(data), {}).copy()
                attrs.update({"usage.contract": "hermes.request.v1",
                              "usage.user.id": attrs.get("usage.user.id", "unattributed"),
                              "usage.request.id": identifier(data.get("api_request_id")) or str(uuid4()),
                              "usage.retry": int(data.get("retry_count") or 0),
                              "usage.outcome": "error",
                              "gen_ai.request.model": identifier(data.get("model")),
                              "gen_ai.provider.name": identifier(data.get("provider"))})
                attrs.update(numeric_usage(data.get("usage")))
                fallback_key = "usage-error:" + str(uuid4())
                tracer.start_span(name="api.error", key=fallback_key, kind="llm", attributes=attrs)
                tracer.end_span(fallback_key, status="error")
            if name == "on_pre_api_request":
                with _lock:
                    attrs = _turns.get(turn_key(data), {}).copy()
                if not attrs:
                    attrs = {"usage.contract": "hermes.request.v1", "usage.user.id": "unattributed",
                             "usage.attribution": "unattributed", "usage.quality": "missing"}
                attrs.update({"usage.request.id": identifier(data.get("api_request_id")) or str(uuid4()),
                              "usage.retry": int(data.get("retry_count") or 0),
                              "usage.quality": "missing", "usage.outcome": "unknown"})
                span = tracer.spans.get_span("api:" + str(data.get("task_id")))
                if span is not None:
                    span.set_attributes(attrs)
                    # A session-root TTL is not a request deadline. A long
                    # in-flight API call must still receive its final usage.
                    tracer._session_keys.get(data.get("session_id"), set()).discard(
                        "api:" + str(data.get("task_id")))
            elif name == "on_post_llm_call":
                with _lock:
                    _turns.pop(turn_key(data), None)
                _current.set(None)
            elif name == "on_subagent_stop":
                with _lock:
                    _children.pop(data.get("child_session_id"), None)
            return result
        setattr(hooks, name, callback)

    for name in ("on_pre_llm_call", "on_post_llm_call", "on_pre_api_request",
                 "on_post_api_request", "on_api_request_error", "on_subagent_start", "on_subagent_stop"):
        wrap(name)


def clean_span(span):
    """Construct a fresh allowlisted span BEFORE the SDK's persistent/async path."""
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.trace import Status, SpanContext
    a = dict(span.attributes or {})
    if a.get("usage.contract") != "hermes.request.v1" or not span.name.startswith("api."):
        return None
    strings = {
        "usage.contract", "usage.turn.id", "usage.session.id", "usage.parent.turn.id",
        "usage.parent.session.id", "usage.transport", "usage.attribution", "usage.user.id",
        "usage.thread.kind", "usage.thread.id", "usage.channel.id", "usage.profile",
        "usage.request.id", "usage.quality", "usage.outcome", "gen_ai.request.model",
        "gen_ai.response.model", "gen_ai.provider.name",
    }
    numbers = {"usage.retry"} | {"usage.tokens." + k for k in
               ("input", "output", "total", "cache_read", "cache_write", "reasoning")}
    attrs = {k: v for k, v in a.items() if
             (k in strings and isinstance(v, str) and len(v) <= 200) or
             (k in numbers and isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 2**63-1)}
    resource = {k: v for k, v in span.resource.attributes.items() if k in
                {"service.name", "service.namespace", "service.instance.id"}}
    context = SpanContext(span.context.trace_id, span.context.span_id, False, span.context.trace_flags)
    return ReadableSpan(name="gen_ai.request", context=context, parent=None,
                        resource=Resource(resource), attributes=attrs,
                        start_time=span.start_time, end_time=span.end_time,
                        status=Status(span.status.status_code), events=(), links=())


class UsageProcessor(SpanProcessor):
    def __init__(self, downstream):
        self.downstream = downstream

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span):
        clean = clean_span(span)
        if clean is not None:
            self.downstream.on_end(clean)

    def shutdown(self):
        self.downstream.shutdown()

    def force_flush(self, timeout_millis=30000):
        return self.downstream.force_flush(timeout_millis)
