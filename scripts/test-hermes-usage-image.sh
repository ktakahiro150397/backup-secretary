#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
image=${1:?supply the tested usage image ID}
docker run --rm --network none --memory 384m --cpus 1 \
  --tmpfs /opt/testhome:rw,nosuid,size=32m,uid=1000,gid=1000,mode=0700 \
  -e HOME=/opt/testhome -e HERMES_HOME=/opt/testhome \
  -e HERMES_OTEL_USAGE_ONLY=true \
  -v "${repo_dir}/observability/hermes-otel/main-windows.yaml:/run/usage.yaml:ro" \
  -v "${repo_dir}/scripts/test_usage_contract.py:/tmp/test_usage_contract.py:ro" \
  --entrypoint bash "${image}" -c '
    set -euo pipefail
    mkdir -p /opt/testhome/.hermes/plugins/hermes_otel
    cp /run/usage.yaml /opt/testhome/.hermes/plugins/hermes_otel/config.yaml
    hermes plugins enable --no-allow-tool-override hermes_otel >/dev/null
    python -c "from hermes_cli.plugins import get_plugin_manager; m=get_plugin_manager(); m.discover_and_load(force=True); p=m._plugins.get(\"hermes_otel\"); assert p and p.enabled and not p.error; print(\"USAGE_PLUGIN_LOAD_OK\")"
    python /tmp/test_usage_contract.py -v
  '
