# SearXNG Self-Hosted Search Setup

> Replaces paid search providers (tably, Brave, SerpAPI) with a zero-cost, self-hosted meta-search engine.

## Architecture

```
Hermes Agent (container)
  ↓ MCP: mcp-searxng
SearXNG (container: http://searxng:8080)
  ↓ meta-search (Google, Bing, DuckDuckGo ...)
Redis/Valkey (container: caching & rate-limiting)
```

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

Uncomment the `mcp_servers` block in your active Hermes config (e.g. `runtime/hermes-data/config.yaml`), or copy from `config/hermes-config.poc.yaml`:

```yaml
mcp_servers:
  searxng:
    command: uvx
    args: [mcp-searxng]
    env:
      SEARXNG_BASE_URL: "http://searxng:8080"
```

Restart Hermes:

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
| `Connection refused` from Hermes | Ensure `SEARXNG_BASE_URL` uses `http://searxng:8080` (Docker DNS), not `localhost`. |
| MCP returns empty results | Check `settings.yml` has `json` in `search.formats`. |
| Some engines time out | SearXNG picks engines automatically; slow ones are skipped. No action needed. |
| `uvx` not found in Hermes container | Use absolute path: `command: /usr/local/bin/uvx` or wherever `uv` is installed. |

## Resources

- [SearXNG docs](https://docs.searxng.org/)
- [mcp-searxng](https://github.com/SecretiveShell/MCP-searxng)
- [mcp-crawl4ai](https://github.com/unclecode/crawl4ai)
- Reference article: [API代0円！SearXNG + Crawl4AI で完全無料](https://note.com/zephel01/n/n1983bb94f996)
