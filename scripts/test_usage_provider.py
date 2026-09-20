"""Explicit opt-in: one real provider request, no tools/context/history.

Run inside a deployed usage image as the normal Hermes user. This is a CLI
verification request and must remain unattributed, never a forged Discord user.
"""
import argparse
import contextlib
import io
import json
import uuid

p=argparse.ArgumentParser()
p.add_argument("--model",required=True)
p.add_argument("--provider",required=True)
a=p.parse_args()
# The model output and incidental SDK output are never saved or reported.
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    from run_agent import AIAgent
    agent=AIAgent(model=a.model,provider=a.provider,requested_provider=a.provider,
        enabled_toolsets=[],disabled_toolsets=["all"],max_iterations=1,
        quiet_mode=True,save_trajectories=False,skip_context_files=True,
        skip_memory=True,skip_background_review=True,load_soul_identity=False,
        platform="cli",session_id="usage-verification-"+uuid.uuid4().hex,
        run_budget_seconds=45,reasoning_config={"effort":"low"})
    assert agent.provider==a.provider
    result=agent.run_conversation("Return exactly OK.",system_message="Non-sensitive usage integration verification. Return OK; do not call tools.")
    from plugins.hermes_otel.tracer import get_tracer
    get_tracer()._force_flush()
print(json.dumps({"provider":a.provider,"model":a.model,"completed":bool(result.get("final_response"))}))
