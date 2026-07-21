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
  docker compose run --rm --no-deps "${service}" bash -lc '
    set -euo pipefail
    umask 077
    config="${HERMES_HOME}/config.yaml"
    if [[ ! -f "${config}" ]]; then
      echo "Missing Hermes config.yaml" >&2
      exit 3
    fi
    backup="${config}.phase1-otel-backup"
    if [[ ! -e "${backup}" ]]; then
      cp -- "${config}" "${backup}"
    fi
    exec hermes plugins enable --no-allow-tool-override hermes_otel
  '
}

enable_for_service hermes
enable_for_service hermes-owashota

echo "hermes_otel is enabled for main and owashota; original configs have local rollback backups."
