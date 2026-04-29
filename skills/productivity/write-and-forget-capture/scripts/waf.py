#!/usr/bin/env python3
"""Write-And-Forget capture MVP.

Stores quick private notes in a local SQLite database with an FTS5 index.
This tool intentionally does not write to Google Tasks, Calendar, GitHub, or
Obsidian. External side effects belong in a later explicit approval flow.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(os.environ.get("WAF_DB", "/opt/data/waf/waf.db"))
VALID_STATUSES = {"open", "suggested", "actioned", "dismissed", "closed"}


SCHEMA = """
create table if not exists notes (
    id integer primary key autoincrement,
    body text not null,
    source text not null default 'manual',
    status text not null default 'open'
        check (status in ('open', 'suggested', 'actioned', 'dismissed', 'closed')),
    tags_json text not null default '[]',
    created_at text not null,
    updated_at text not null
);

create virtual table if not exists notes_fts using fts5(
    body,
    tags,
    tokenize='trigram'
);

create table if not exists suggestions (
    id integer primary key autoincrement,
    note_id integer not null references notes(id) on delete cascade,
    kind text not null,
    title text not null,
    payload_json text not null default '{}',
    status text not null default 'open'
        check (status in ('open', 'actioned', 'dismissed')),
    created_at text not null,
    updated_at text not null
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        tag = part.strip()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("pragma foreign_keys = on")
    con.executescript(SCHEMA)
    return con


def note_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["tags"] = json.loads(data.pop("tags_json"))
    return data


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def capture(con: sqlite3.Connection, body: str, source: str, tags: list[str]) -> dict[str, Any]:
    body = body.strip()
    if not body:
        raise ValueError("body must not be empty")
    now = utc_now()
    tags_json = json.dumps(tags, ensure_ascii=False)
    cur = con.execute(
        """
        insert into notes(body, source, status, tags_json, created_at, updated_at)
        values (?, ?, 'open', ?, ?, ?)
        """,
        (body, source.strip() or "manual", tags_json, now, now),
    )
    note_id = int(cur.lastrowid)
    con.execute(
        "insert into notes_fts(rowid, body, tags) values (?, ?, ?)",
        (note_id, body, " ".join(tags)),
    )
    con.commit()
    row = con.execute("select * from notes where id = ?", (note_id,)).fetchone()
    assert row is not None
    return {"status": "captured", "note": note_to_dict(row)}


def search(con: sqlite3.Connection, query: str, include_closed: bool, limit: int) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    status_filter = "" if include_closed else "and n.status in ('open', 'suggested')"
    rows = con.execute(
        f"""
        select n.*
        from notes_fts f
        join notes n on n.id = f.rowid
        where notes_fts match ?
        {status_filter}
        order by bm25(notes_fts), n.created_at desc
        limit ?
        """,
        (query, limit),
    ).fetchall()
    return {"status": "ok", "results": [note_to_dict(row) for row in rows]}


def update_status(con: sqlite3.Connection, note_id: int, status: str) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    now = utc_now()
    cur = con.execute(
        "update notes set status = ?, updated_at = ? where id = ?",
        (status, now, note_id),
    )
    if cur.rowcount == 0:
        raise LookupError(f"note not found: {note_id}")
    con.commit()
    row = con.execute("select * from notes where id = ?", (note_id,)).fetchone()
    assert row is not None
    return {"status": "updated", "note": note_to_dict(row)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write-And-Forget capture MVP")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"SQLite DB path (default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="command", required=True)

    capture_parser = sub.add_parser("capture", help="Capture a note into the WAF inbox")
    capture_parser.add_argument("body", help="Note body")
    capture_parser.add_argument("--source", default="manual", help="Source label, e.g. discord/manual")
    capture_parser.add_argument("--tags", default="", help="Comma-separated tags")

    search_parser = sub.add_parser("search", help="Search captured notes with SQLite FTS5")
    search_parser.add_argument("query", help="FTS query")
    search_parser.add_argument("--include-closed", action="store_true", help="Include closed/actioned/dismissed notes")
    search_parser.add_argument("--limit", type=int, default=20, help="Maximum results")

    status_parser = sub.add_parser("status", help="Update note status")
    status_parser.add_argument("note_id", type=int, help="Note ID")
    status_parser.add_argument("status", choices=sorted(VALID_STATUSES), help="New status")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        with connect(args.db) as con:
            if args.command == "capture":
                emit(capture(con, args.body, args.source, parse_tags(args.tags)))
            elif args.command == "search":
                emit(search(con, args.query, args.include_closed, args.limit))
            elif args.command == "status":
                emit(update_status(con, args.note_id, args.status))
            else:  # pragma: no cover - argparse prevents this
                parser.error(f"unknown command: {args.command}")
    except (ValueError, LookupError, sqlite3.Error) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
