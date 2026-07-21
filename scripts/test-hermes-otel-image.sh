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

from hermes_otel.plugin_config import load_config

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

hermes plugins enable --no-allow-tool-override hermes_otel >/dev/null
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
assert matches[0].get("enabled") is True
assert not matches[0].get("error")
print("PLUGIN_ENABLED_OK")
'
CONTAINER_SCRIPT
