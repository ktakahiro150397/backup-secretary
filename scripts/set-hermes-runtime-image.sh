#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
env_file="${repo_dir}/.env"
image="backup-secretary/hermes-agent:local"

if [[ ! -f "${env_file}" || -L "${env_file}" ]]; then
  echo "Expected a regular non-symlink root .env at ${env_file}." >&2
  exit 2
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup="${env_file}.pre-observability-${timestamp}"
temporary=$(mktemp "${repo_dir}/.env.tmp.XXXXXX")
trap 'rm -f -- "${temporary}"' EXIT

cp -p -- "${env_file}" "${backup}"
awk -v image="${image}" '
  BEGIN { replaced = 0 }
  /^HERMES_IMAGE=/ {
    if (!replaced) {
      print "HERMES_IMAGE=" image
      replaced = 1
    }
    next
  }
  { print }
  END {
    if (!replaced) {
      print "HERMES_IMAGE=" image
    }
  }
' "${env_file}" >"${temporary}"

chmod --reference="${env_file}" "${temporary}"
mv -- "${temporary}" "${env_file}"
trap - EXIT

echo "Updated root .env to the verified local Hermes image; prior file retained in an ignored timestamped backup."
