#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "${repo_dir}"

if ! docker network inspect local-observability-net >/dev/null 2>&1; then
  echo "Missing external network local-observability-net; prepare the standalone observability stack first." >&2
  exit 2
fi

enable_for_service() {
  local service=$1
  local config_owner
  config_owner=$(docker compose run --rm --no-deps --entrypoint stat "${service}" -c '%u:%g' /opt/data/config.yaml | tail -n 1)
  if [[ ! "${config_owner}" =~ ^[0-9]+:[0-9]+$ ]]; then
    echo "Could not determine config.yaml ownership for ${service}." >&2
    exit 3
  fi
  docker compose run --rm --no-deps --user "${config_owner}" --entrypoint bash "${service}" -c '
    set -euo pipefail
    umask 077
    config="${HERMES_HOME}/config.yaml"
    if [[ ! -f "${config}" ]]; then
      echo "Missing Hermes config.yaml" >&2
      exit 4
    fi
    backup="${config}.phase1-otel-backup"
    if [[ ! -e "${backup}" ]]; then
      cp -- "${config}" "${backup}"
    fi
    exec hermes plugins enable --no-allow-tool-override hermes_otel
  '
}

enable_for_service hermes-main
enable_for_service hermes-owashota

echo "hermes_otel is enabled for main and owashota; original configs have local rollback backups."
