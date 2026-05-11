#!/usr/bin/env python3
"""Minimal MCP server for SearXNG search (raw JSON-RPC over stdio).

Usage:  python /opt/data/mcp-searxng-server.py

Environment:
    SEARXNG_URL  - SearXNG base URL (default: http://localhost:8080)
"""

import json
import os
import sys
import httpx

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://searxng:8080")


def send_message(msg: dict) -> None:
    data = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(data)}\r\n\r\n{data}")
    sys.stdout.flush()


def read_message() -> dict | None:
    line = sys.stdin.readline()
    if not line:
        return None
    if not line.startswith("Content-Length:"):
        # Handle stray notifications
        return json.loads(line.strip()) if line.strip() else None
    length = int(line.split(":", 1)[1].strip())
    sys.stdin.readline()  # blank
    data = sys.stdin.read(length)
    return json.loads(data)


def handle_initialize(params: dict) -> dict:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "searxng", "version": "0.1.0"},
    }


def handle_tools_list(params: dict) -> dict:
    return {
        "tools": [
            {
                "name": "search",
                "description": (
                    "Search the web using SearXNG. Aggregates results from Google, Bing, "
                    "DuckDuckGo and many others. Use this to find information on the web."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {
                            "type": "integer",
                            "description": "Max number of results (default: 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            }
        ]
    }


def do_search(query: str, limit: int = 5) -> str:
    with httpx.Client(base_url=SEARXNG_URL, timeout=30.0) as client:
        resp = client.get("/search", params={"q": query, "format": "json"})
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    total = data.get("number_of_results", len(results))

    lines = [f"Query: {query}", f"Total results: {total}", ""]
    for i, r in enumerate(results[:limit], 1):
        lines.append(f"[{i}] {r.get('title', 'No title')}")
        lines.append(f"    URL: {r.get('url', 'N/A')}")
        lines.append(f"    {r.get('content', 'No snippet')}")
        lines.append("")

    if not results:
        lines.append("No results found.")

    return "\n".join(lines)


def handle_tools_call(params: dict) -> dict:
    name = params.get("name", "")
    arguments = params.get("arguments", {})

    if name == "search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        try:
            text = do_search(query, int(limit))
            return {
                "content": [{"type": "text", "text": text}],
                "isError": False,
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Search error: {e}"}],
                "isError": True,
            }

    return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}


def main():
    while True:
        msg = read_message()
        if msg is None:
            break

        # Skip notifications (no id)
        if "id" not in msg:
            continue

        msg_id = msg["id"]
        method = msg.get("method", "")
        params = msg.get("params", {})

        try:
            if method == "initialize":
                result = handle_initialize(params)
            elif method == "tools/list":
                result = handle_tools_list(params)
            elif method == "tools/call":
                result = handle_tools_call(params)
            else:
                result = None

            send_message({"jsonrpc": "2.0", "id": msg_id, "result": result})
        except Exception as e:
            send_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": str(e)},
            })


if __name__ == "__main__":
    main()
