#!/usr/bin/env python3
"""Migrate legacy Hermes messages with original timestamps to OpenViking."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

TIME_COLUMNS = ("created_at", "started_at", "start_time", "timestamp", "updated_at")


def parse_time(value):
    if isinstance(value, (int, float)) or str(value).replace(".", "", 1).isdigit():
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000
        return dt.datetime.fromtimestamp(number, dt.timezone.utc)
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone(dt.timedelta(hours=9)))
    return parsed


def post_batch(args, session_id, messages):
    headers = {"Content-Type": "application/json", "X-OpenViking-Actor-Peer": args.agent}
    if args.api_key:
        headers.update({"X-API-Key": args.api_key, "Authorization": f"Bearer {args.api_key}"})
    else:
        headers.update({"X-OpenViking-Account": args.account, "X-OpenViking-User": args.user})
    url = f"{args.endpoint.rstrip('/')}/api/v1/sessions/{session_id}/messages/batch"
    body = json.dumps({"messages": messages}, ensure_ascii=False).encode()
    request = urllib.request.Request(url, body, headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"OpenViking HTTP {error.code}: {detail[:500]}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--after", default="2026-05-01T00:00:00+09:00")
    parser.add_argument("--before", default="2026-05-08T00:00:00+09:00")
    parser.add_argument("--endpoint", default=os.getenv("OPENVIKING_ENDPOINT", "http://127.0.0.1:1933"))
    parser.add_argument("--account", default=os.getenv("OPENVIKING_ACCOUNT", ""))
    parser.add_argument("--user", default=os.getenv("OPENVIKING_USER", ""))
    parser.add_argument("--agent", default=os.getenv("OPENVIKING_AGENT", "hermes-owashota"))
    parser.add_argument("--api-key", default=os.getenv("OPENVIKING_API_KEY", ""))
    parser.add_argument("--manifest", type=Path, default=Path("runtime/migrations/owashota-20260501-07-v2.jsonl"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.db.is_file():
        parser.error(f"database not found: {args.db}")
    after, before = parse_time(args.after), parse_time(args.before)
    db = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    session_cols = {row[1] for row in db.execute("PRAGMA table_info(sessions)")}
    message_cols = {row[1] for row in db.execute("PRAGMA table_info(messages)")}
    session_time_col = next((name for name in TIME_COLUMNS if name in session_cols), None)
    message_time_col = next((name for name in TIME_COLUMNS if name in message_cols), None)
    if not session_time_col or "id" not in session_cols:
        parser.error(f"unsupported sessions schema: {sorted(session_cols)}")
    if not {"session_id", "role", "content"} <= message_cols or not message_time_col:
        parser.error(f"unsupported messages schema: {sorted(message_cols)}")

    sessions = []
    for row in db.execute(f"SELECT id, {session_time_col} AS session_time FROM sessions"):
        try:
            when = parse_time(row["session_time"])
        except (TypeError, ValueError, OSError):
            continue
        if after <= when < before:
            sessions.append((row["id"], when))
    sessions.sort(key=lambda item: item[1])
    if args.limit is not None:
        sessions = sessions[:args.limit]

    total = written = 0
    order = "timestamp, id" if {"timestamp", "id"} <= message_cols else "rowid"
    for session_id, when in sessions:
        query = (
            f"SELECT role, content, {message_time_col} AS message_time "
            f"FROM messages WHERE session_id=? ORDER BY {order}"
        )
        messages = []
        for row in db.execute(query, (session_id,)):
            if row["role"] not in {"user", "assistant"} or not row["content"]:
                continue
            message = {
                "role": row["role"],
                "parts": [{"type": "text", "text": str(row["content"])}],
                "created_at": parse_time(row["message_time"]).astimezone(dt.timezone.utc).isoformat(),
            }
            if row["role"] == "assistant":
                message["peer_id"] = args.agent
            messages.append(message)
        first_time = messages[0]["created_at"] if messages else "-"
        last_time = messages[-1]["created_at"] if messages else "-"
        print(f"{session_id}\t{len(messages)} messages\t{first_time}\t{last_time}")
        total += len(messages)
        if not args.apply or not messages:
            continue
        for start in range(0, len(messages), 100):
            post_batch(args, session_id, messages[start:start + 100])
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open("a", encoding="utf-8") as output:
            output.write(json.dumps({
                "source_session_id": session_id,
                "ov_session_id": session_id,
                "started_at": when.isoformat(),
                "message_count": len(messages),
                "first_message_at": first_time,
                "last_message_at": last_time,
            }, ensure_ascii=False) + "\n")
        written += 1
    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(sessions)} sessions, {total} messages, {written} written")


if __name__ == "__main__":
    main()
