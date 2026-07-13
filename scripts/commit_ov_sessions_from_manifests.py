#!/usr/bin/env python3
"""Resume OpenViking session commits from migration manifests safely."""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

TERMINAL_STATES = {"completed", "failed"}


def request_json(args, method, path, body=None):
    headers = {
        "Accept": "application/json",
        "X-API-Key": args.api_key,
        "Authorization": f"Bearer {args.api_key}",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    request = urllib.request.Request(
        f"{args.endpoint.rstrip('/')}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=args.request_timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"OpenViking HTTP {error.code}: {detail[:500]}") from error
    if payload.get("status") == "error" or payload.get("ok") is False:
        raise RuntimeError(f"OpenViking error: {payload.get('error', payload)}")
    return payload.get("result", payload.get("data", payload))


def load_sessions(manifests):
    sessions = {}
    for manifest in manifests:
        for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            session_id = row.get("ov_session_id")
            if not session_id:
                raise ValueError(f"{manifest}:{line_number}: missing ov_session_id")
            sessions.setdefault(session_id, row)
    return sorted(
        sessions.values(),
        key=lambda row: (row.get("started_at", ""), row["ov_session_id"]),
    )


def append_event(path, event):
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(event, ensure_ascii=False) + "\n")


def wait_for_task(args, task_id):
    deadline = time.monotonic() + args.task_timeout
    while True:
        task = request_json(args, "GET", f"/api/v1/tasks/{task_id}")
        if task.get("status") in TERMINAL_STATES:
            return task
        if time.monotonic() >= deadline:
            raise TimeoutError(f"task {task_id} did not finish within {args.task_timeout}s")
        time.sleep(args.poll_interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument(
        "--endpoint", default=os.getenv("OPENVIKING_ENDPOINT", "http://127.0.0.1:1933")
    )
    parser.add_argument("--api-key", default=os.getenv("OPENVIKING_API_KEY", ""))
    parser.add_argument("--limit", type=int, help="maximum uncommitted sessions to process")
    parser.add_argument("--progress", type=Path, help="append-only JSONL progress log")
    parser.add_argument("--poll-interval", type=float, default=10)
    parser.add_argument("--request-timeout", type=float, default=60)
    parser.add_argument("--task-timeout", type=float, default=3600)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    missing = [str(path) for path in args.manifest if not path.is_file()]
    if missing:
        parser.error(f"manifest not found: {', '.join(missing)}")
    if not args.api_key:
        parser.error("OPENVIKING_API_KEY or --api-key is required")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if min(args.poll_interval, args.request_timeout, args.task_timeout) <= 0:
        parser.error("timeout and interval values must be positive")

    sessions = load_sessions(args.manifest)
    committed = empty = selected = completed = 0
    print(f"loaded {len(sessions)} unique sessions from {len(args.manifest)} manifest(s)")

    for row in sessions:
        session_id = row["ov_session_id"]
        meta = request_json(args, "GET", f"/api/v1/sessions/{session_id}")
        if int(meta.get("commit_count", 0)) > 0:
            committed += 1
            print(f"SKIP committed {session_id}")
            continue
        if int(meta.get("message_count", 0)) == 0:
            empty += 1
            print(f"SKIP empty {session_id}")
            continue
        if args.limit is not None and selected >= args.limit:
            continue
        selected += 1
        print(
            f"{'COMMIT' if args.apply else 'WOULD COMMIT'} {session_id} "
            f"({meta.get('message_count', '?')} messages, {meta.get('pending_tokens', '?')} tokens)",
            flush=True,
        )
        if not args.apply:
            continue

        result = request_json(
            args, "POST", f"/api/v1/sessions/{session_id}/commit", {"keep_recent_count": 0}
        )
        task_id = result.get("task_id")
        if not task_id:
            raise RuntimeError(f"commit for {session_id} returned no task_id: {result}")
        append_event(args.progress, {
            "session_id": session_id,
            "status": "submitted",
            "task_id": task_id,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        task = wait_for_task(args, task_id)
        status = task.get("status")
        append_event(args.progress, {
            "session_id": session_id,
            "status": status,
            "task_id": task_id,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": task.get("error"),
        })
        if status != "completed":
            raise RuntimeError(f"memory extraction failed for {session_id}: {task.get('error', task)}")
        completed += 1
        print(f"DONE {session_id} task={task_id}", flush=True)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(
        f"{mode}: {len(sessions)} total, {committed} already committed, {empty} empty, "
        f"{selected} selected, {completed} completed"
    )


if __name__ == "__main__":
    main()
