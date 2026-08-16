#!/bin/sh
set -eu

# Print only resource-control metadata and cgroup counters. Deliberately avoid
# process arguments, application logs, prompts, sender IDs, and credentials.
for service in hermes-main hermes-owashota; do
  container_id=$(docker compose ps -q "$service")
  if [ -z "$container_id" ]; then
    printf 'service=%s state=not-running\n' "$service"
    continue
  fi

  docker inspect --format \
    'service='"$service"' state={{.State.Status}} restart_count={{.RestartCount}} oom_killed={{.State.OOMKilled}} pids_limit={{.HostConfig.PidsLimit}} memory_limit_bytes={{.HostConfig.Memory}} memory_swap_limit_bytes={{.HostConfig.MemorySwap}}' \
    "$container_id"

  docker compose exec -T "$service" sh -c '
    printf "pids_current="; cat /sys/fs/cgroup/pids.current
    printf "memory_current_bytes="; cat /sys/fs/cgroup/memory.current
    printf "memory_swap_current_bytes="; cat /sys/fs/cgroup/memory.swap.current
    printf "memory_events="; tr "\n" " " < /sys/fs/cgroup/memory.events; printf "\n"
  '
done
