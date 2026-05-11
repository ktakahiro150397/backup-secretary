#!/usr/bin/env python3
"""Minimal MCP server for SearXNG search (JSON-RPC over stdio).

Supports BOTH Content-Length framing (standard MCP) and NDJSON (line-delimited)
to remain compatible with clients that read line-by-line.

Usage:  python3 /opt/data/mcp-searxng-server.py

Environment:
    SEARXNG_URL  - SearXNG base URL (default: http://searxng:8080)
"""

import json
import os
import sys
import httpx

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://searxng:8080")


def send_message(msg: dict) -> None:
    """Send a JSON-RPC message using NDJSON (line-delimited) format.
    
    Hermes' MCP client reads stdout line-by-line and parses each line as JSON.
    Content-Length framing causes it to try parsing 'Content-Length: ...' as JSON.
    """
    data = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(data + "\n")
    sys.stdout.flush()


def read_message() -> dict | None:
    """Read a JSON-RPC message from stdin.
    
    Supports both Content-Length framing (standard MCP) and NDJSON.
    """
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        stripped = line.strip()
        if not stripped:
            continue
        
        # Content-Length framing
        if stripped.startswith("Content-Length:"):
            length = int(stripped.split(":", 1)[1].strip())
            # consume blank line
            sys.stdin.readline()
            # read exact body
            data = sys.stdin.read(length)
            return json.loads(data)
        
        # NDJSON (line-delimited JSON)
        return json.loads(stripped)


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
