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
  npm cache clean --force; \
  # Install Scrapling for web extraction fallback (stealthy_fetch / fetch for JS-required & bot-protected sites)
  . /opt/hermes/.venv/bin/activate && uv pip install --no-cache-dir "scrapling[ai]"; \
  # Install messaging platform deps (discord, telegram, slack) at build time
  # because lazy_deps.py fails after usermod changes the hermes user's UID,
  # making the venv site-packages unwritable at runtime.
  . /opt/hermes/.venv/bin/activate && uv pip install --no-cache-dir \
    "discord.py[voice]==2.7.1" \
    "brotlicffi==1.2.0.1" \
    "python-telegram-bot[webhooks]==22.6" \
    "aiohttp==3.13.3" \
    "slack-bolt==1.27.0" \
    "slack-sdk==3.40.1"; \
  if [ "$HERMES_GID" != "$(id -g hermes)" ]; then \
  groupmod -o -g "$HERMES_GID" hermes; \
  fi; \
  if [ "$HERMES_UID" != "$(id -u hermes)" ]; then \
  usermod -u "$HERMES_UID" hermes; \
  fi; \
  # Re-chown the venv after usermod so the hermes user can write to it
  # (needed for lazy_deps.py installs at runtime).
  chown -R hermes:hermes /opt/hermes/.venv; \
  mkdir -p /opt/data; \
  chown -R hermes:hermes /opt/data
