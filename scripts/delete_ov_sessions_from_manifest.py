#!/usr/bin/env python3
"""Delete only OpenViking sessions listed in a migration manifest."""

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ALLOWED = re.compile(r"^(?:2026050[1-7]_\d{6}_[a-z0-9]+|cron_[a-z0-9_]+_2026050[1-7]_\d{6})$")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--endpoint", default=os.getenv("OPENVIKING_ENDPOINT", "http://127.0.0.1:1933"))
    parser.add_argument("--api-key", default=os.getenv("OPENVIKING_API_KEY", ""))
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row["ov_session_id"] for row in rows]
    if len(ids) != args.expected_count or len(set(ids)) != len(ids):
        parser.error(f"manifest count/uniqueness mismatch: {len(ids)} rows, {len(set(ids))} unique")
    invalid = [session_id for session_id in ids if not ALLOWED.fullmatch(session_id)]
    if invalid:
        parser.error(f"refusing unexpected session ids: {invalid}")
    if args.apply and not args.api_key:
        parser.error("--apply requires OPENVIKING_API_KEY")

    for session_id in ids:
        print(session_id)
        if not args.apply:
            continue
        url = f"{args.endpoint.rstrip('/')}/api/v1/sessions/{session_id}"
        headers = {"X-API-Key": args.api_key, "Authorization": f"Bearer {args.api_key}"}
        request = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(f"failed deleting {session_id}: HTTP {error.code}: {detail[:300]}") from error
    print(f"{'DELETED' if args.apply else 'DRY-RUN'}: {len(ids)} sessions")


if __name__ == "__main__":
    main()
