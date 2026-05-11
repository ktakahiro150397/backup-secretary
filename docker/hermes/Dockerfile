ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest

FROM ${HERMES_BASE_IMAGE}

ARG HERMES_UID=1000
ARG HERMES_GID=1000

RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends gh rsync; \
  rm -rf /var/lib/apt/lists/*; \
  npm install -g @openai/codex; \
  npm install -g @anthropic-ai/claude-code; \
  npm install -g @jackwener/opencli; \
  npm cache clean --force; \
  # Install Scrapling for web extraction fallback (stealthy_fetch / fetch for JS-required & bot-protected sites)
  . /opt/hermes/.venv/bin/activate && uv pip install --no-cache-dir "scrapling[ai]"; \
  if [ "$HERMES_GID" != "$(id -g hermes)" ]; then \
  groupmod -o -g "$HERMES_GID" hermes; \
  fi; \
  if [ "$HERMES_UID" != "$(id -u hermes)" ]; then \
  usermod -u "$HERMES_UID" hermes; \
  fi; \
  mkdir -p /opt/data; \
  chown -R hermes:hermes /opt/data
