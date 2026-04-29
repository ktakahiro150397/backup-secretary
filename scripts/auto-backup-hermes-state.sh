#!/bin/bash
# Auto-backup Hermes state files to backup-secretary repo
# Only operates on main branch. Safe to run from cron.
set -euo pipefail

REPO_DIR="${REPO_DIR:-/workspace/backup-secretary}"
DATA_DIR="${DATA_DIR:-/opt/data}"
RUNTIME_DIR="$REPO_DIR/runtime/hermes-data"

cd "$REPO_DIR"

# --- guard: only run on main ---
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
    echo "[$(date -Iseconds)] Not on main (current: $BRANCH). Skipping."
    exit 0
fi

# --- pull latest to avoid conflicts ---
git pull origin main --ff-only 2>&1 || {
    echo "[$(date -Iseconds)] git pull failed, aborting to avoid force-push risk."
    exit 1
}

# --- sync files ---
mkdir -p "$RUNTIME_DIR/memories" "$RUNTIME_DIR/cron" "$RUNTIME_DIR/plans"

cp "$DATA_DIR/config.yaml"          "$RUNTIME_DIR/config.yaml"
cp "$DATA_DIR/SOUL.md"              "$RUNTIME_DIR/SOUL.md"
cp "$DATA_DIR/memories/USER.md"     "$RUNTIME_DIR/memories/USER.md"
cp "$DATA_DIR/memories/MEMORY.md"   "$RUNTIME_DIR/memories/MEMORY.md"
cp "$DATA_DIR/cron/jobs.json"       "$RUNTIME_DIR/cron/jobs.json"
cp "$DATA_DIR/plans/"*.md           "$RUNTIME_DIR/plans/" 2>/dev/null || true

# --- stage whitelisted paths ---
git add \
    runtime/hermes-data/config.yaml \
    runtime/hermes-data/SOUL.md \
    runtime/hermes-data/memories/USER.md \
    runtime/hermes-data/memories/MEMORY.md \
    runtime/hermes-data/cron/jobs.json \
    runtime/hermes-data/plans/

# --- commit only if dirty ---
if git diff --cached --quiet; then
    echo "[$(date -Iseconds)] No changes."
    exit 0
fi

git commit -m "chore: auto-backup Hermes state [$(date -u +'%Y-%m-%d %H:%M UTC')]"
git push origin main

echo "[$(date -Iseconds)] Backup committed and pushed."