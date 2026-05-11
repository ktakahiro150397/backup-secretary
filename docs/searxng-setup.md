# SearXNG Self-Hosted Search Setup

> Replaces paid search providers (tably, Brave, SerpAPI) with a zero-cost, self-hosted meta-search engine.

## Architecture

```
Hermes Agent (container)
  ↓ MCP: scripts/mcp-searxng-server.py
SearXNG (container: http://searxng:8080)
  ↓ meta-search (Google, Bing, DuckDuckGo ...)
Redis/Valkey (container: caching & rate-limiting)
```

> **Note:** The official `mcp-searxng` PyPI package (v0.1.0) has compatibility issues with MCP SDK ≥1.2x and returns `Internal Server Error` on initialization. This setup uses a lightweight custom MCP server (`scripts/mcp-searxng-server.py`) instead.

## Quick start

### 1. Environment

`.env.example` already contains the defaults. Copy to `.env` and adjust if needed:

```bash
SEARXNG_BIND=127.0.0.1
SEARXNG_PORT=8080
SEARXNG_CONFIG_DIR=./config/searxng
```

### 2. First boot (auto-generate settings)

```bash
docker compose up -d searxng redis
```

Wait ~10 seconds, then copy the generated settings out:

```bash
docker compose cp searxng:/etc/searxng/settings.yml ./config/searxng/settings.yml
```

### 3. Enable JSON format (required for MCP)

Edit `./config/searxng/settings.yml`:

```yaml
search:
  formats:
    - html
    - json   # <-- add this
```

Restart:

```bash
docker compose restart searxng
```

Verify JSON output:

```bash
curl "http://127.0.0.1:8080/search?q=hello&format=json"
```

### 4. Wire into Hermes

Add the following to your active Hermes config (e.g. `runtime/hermes-data/config.yaml`):

```yaml
mcp_servers:
  searxng:
    command: python
    args: ["/opt/data/mcp-searxng-server.py"]
    env:
      SEARXNG_URL: "http://searxng:8080"
```

> The custom server script is bind-mounted into the Hermes container via `HERMES_DATA_DIR`. Make sure `scripts/mcp-searxng-server.py` exists in the repo root so it is synced into `/opt/data/`.

Restart Hermes to load the new MCP server:

```bash
docker compose restart hermes
```

### 5. Test

Ask Hermes:

> "SearXNG の最新リリース情報を調べて"

If successful, the agent calls `searxng` tool, gets JSON results, and synthesises an answer.

## Optional: Crawl4AI (full-page text extraction)

SearXNG returns snippets. For ad-free article extraction, also enable Crawl4AI:

```yaml
mcp_servers:
  crawl4ai:
    command: uvx
    args:
      - "--from"
      - "mcp-crawl4ai"
      - "crawl4ai-mcp"
```

Install Chromium inside the Hermes container:

```bash
docker compose exec hermes bash -c "playwright install chromium"
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Connection refused` from Hermes | Ensure `SEARXNG_URL` uses `http://searxng:8080` (Docker DNS), not `localhost`. |
| MCP returns empty results | Check `settings.yml` has `json` in `search.formats`. |
| `Internal Server Error` from official `mcp-searxng` | Use the custom server `scripts/mcp-searxng-server.py` instead. |
| Some engines time out | SearXNG picks engines automatically; slow ones are skipped. No action needed. |

## Resources

- [SearXNG docs](https://docs.searxng.org/)
- [mcp-searxng (official, broken on MCP SDK ≥1.2x)](https://github.com/SecretiveShell/MCP-searxng)
- [mcp-crawl4ai](https://github.com/unclecode/crawl4ai)
- Reference article: [API代0円！SearXNG + Crawl4AI で完全無料](https://note.com/zephel01/n/n1983bb94f996)
