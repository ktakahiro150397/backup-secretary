# SearXNG configuration

This directory is mounted read-only at `/etc/searxng`.

## Purpose

- Hermes uses `http://searxng:8080` through the shared Docker network.
- JSON output is enabled because the Hermes SearXNG provider uses the JSON API.
- Valkey stores limiter state and other short-lived shared data.
- The host port is bound to `127.0.0.1` by default and is intended only for diagnostics.

## Start and verify

```bash
docker compose up -d valkey searxng
curl -fsS "http://127.0.0.1:8080/search?q=OpenViking&format=json"
```

A successful response contains a JSON object with a `results` array.

## Security

No fixed `server.secret_key` is committed to the repository. Keep `SEARXNG_BIND=127.0.0.1` unless access is protected by a VPN or reverse proxy. If SearXNG is exposed outside the host, configure a deployment-specific secret through an untracked local settings override or another secret-management mechanism.

## Hermes configuration

Each Hermes instance has:

```yaml
web:
  search_backend: searxng
```

The Compose common environment supplies:

```text
SEARXNG_URL=http://searxng:8080
```

SearXNG provides web search only. Page extraction remains unset and can be added separately later.
