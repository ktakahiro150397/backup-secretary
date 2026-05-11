# SearXNG Configuration

This directory is mounted to `/etc/searxng` inside the SearXNG container.

## First-boot workflow

1. Start the service (settings are auto-generated on first boot):
   ```bash
   docker compose up -d searxng redis
   ```
2. Copy the generated `settings.yml` out of the container:
   ```bash
   docker compose cp searxng:/etc/searxng/settings.yml ./config/searxng/settings.yml
   ```
3. Edit `./config/searxng/settings.yml` and add `json` to `search.formats`:
   ```yaml
   search:
     formats:
       - html
       - json   # <-- add this (required for MCP)
   ```
4. Restart SearXNG:
   ```bash
   docker compose restart searxng
   ```
5. Verify JSON output works:
   ```bash
   curl "http://127.0.0.1:8080/search?q=hello&format=json"
   ```

## Hermes MCP integration

Add the following to your active `config.yaml` (e.g. `runtime/hermes-data/config.yaml`):

```yaml
mcp_servers:
  searxng:
    command: uvx
    args: [mcp-searxng]
    env:
      SEARXNG_BASE_URL: "http://searxng:8080"
```

> Use `http://searxng:8080` from inside the Docker network (Hermes container → SearXNG container).
> Use `http://127.0.0.1:8080` from the Docker host.

## Optional: Crawl4AI for full-page fetch

If you also want ad-free article extraction, add the Crawl4AI MCP server:

```yaml
mcp_servers:
  crawl4ai:
    command: uvx
    args:
      - "--from"
      - "mcp-crawl4ai"
      - "crawl4ai-mcp"
```

Install Chromium inside the Hermes container first:
```bash
docker compose exec hermes bash -c "playwright install chromium"
```
