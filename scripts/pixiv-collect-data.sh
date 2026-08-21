#!/usr/bin/env bash
set -euo pipefail

# Hermes cron entry point. Keep the implementation in the pixiv-watcher repo
# so manual runs and scheduled runs cannot drift apart.
exec /opt/data/repos/pixiv-watcher/scripts/collect.sh
