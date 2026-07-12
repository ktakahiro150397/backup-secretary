#!/usr/bin/env python3
"""Idempotently add filtering and pagination to Hermes viking_browse."""
import argparse
from pathlib import Path

SCHEMA_MARKER = '"description": "Optional entry-name prefix filter'
SCHEMA_NEEDLE = '''            "path": {
                "type": "string",
                "description": "Viking URI path (default: viking://). Examples: 'viking://resources/', 'viking://user/memories/'.",
            },
'''
SCHEMA_REPLACEMENT = SCHEMA_NEEDLE + '''            "prefix": {
                "type": "string",
                "description": "Optional entry-name prefix filter, for example '20260507'.",
            },
            "limit": {
                "type": "integer", "minimum": 1, "maximum": 2000,
                "description": "Maximum entries to return (default: 50, maximum: 2000).",
            },
            "offset": {
                "type": "integer", "minimum": 0,
                "description": "Number of matching entries to skip (default: 0).",
            },
'''

BROWSE_NEEDLE = '''            if isinstance(raw_entries, list):
                entries = []
                for e in raw_entries[:50]:  # cap at 50 entries
                    uri = e.get("uri", "")
                    name = e.get("rel_path") or e.get("name") or (uri.rsplit("/", 1)[-1] if uri else "")
                    is_dir = bool(e.get("isDir") or e.get("is_dir") or e.get("type") == "dir")
                    entries.append({
                        "name": name,
                        "uri": uri,
                        "type": "dir" if is_dir else "file",
                        "abstract": e.get("abstract", ""),
                    })
                return json.dumps({"path": path, "entries": entries}, ensure_ascii=False)
'''
BROWSE_REPLACEMENT = '''            if isinstance(raw_entries, list):
                prefix = args.get("prefix", "")
                if not isinstance(prefix, str):
                    prefix = ""
                try:
                    limit = max(1, min(2000, int(args.get("limit", 50))))
                    offset = max(0, int(args.get("offset", 0)))
                except (TypeError, ValueError):
                    return tool_error("limit and offset must be integers")

                matched_entries = []
                for e in raw_entries:
                    uri = e.get("uri", "")
                    name = e.get("rel_path") or e.get("name") or (uri.rsplit("/", 1)[-1] if uri else "")
                    if not prefix or name.startswith(prefix):
                        matched_entries.append((e, uri, name))

                total = len(matched_entries)
                selected = matched_entries[offset:offset + limit]
                entries = []
                for e, uri, name in selected:
                    is_dir = bool(e.get("isDir") or e.get("is_dir") or e.get("type") == "dir")
                    entries.append({
                        "name": name, "uri": uri,
                        "type": "dir" if is_dir else "file",
                        "abstract": e.get("abstract", ""),
                    })
                next_offset = offset + len(entries)
                has_more = next_offset < total
                return json.dumps({
                    "path": path, "prefix": prefix, "offset": offset,
                    "limit": limit, "total": total, "returned": len(entries),
                    "has_more": has_more,
                    "next_offset": next_offset if has_more else None,
                    "entries": entries,
                }, ensure_ascii=False)
'''

def replace_once(source, old, new, label):
    if new in source:
        return source
    if source.count(old) != 1:
        raise RuntimeError(f"unexpected Hermes source: {label} block not found exactly once")
    return source.replace(old, new, 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    original = args.target.read_text(encoding="utf-8")
    patched = replace_once(original, SCHEMA_NEEDLE, SCHEMA_REPLACEMENT, "schema")
    patched = replace_once(patched, BROWSE_NEEDLE, BROWSE_REPLACEMENT, "browse")
    if args.check and patched != original:
        raise RuntimeError("target is not patched")
    if not args.check and patched != original:
        args.target.write_text(patched, encoding="utf-8")
    print(("patched" if patched != original else "already patched") + f": {args.target}")

if __name__ == "__main__":
    main()
