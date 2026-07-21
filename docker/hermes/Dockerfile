ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent@sha256:00f57d79b2b20745a4f2c47bd26135f0473100ca23103ffc3eb3f89f3f6cef50

FROM ${HERMES_BASE_IMAGE}

ARG HERMES_UID=1000
ARG HERMES_GID=1000
ARG HERMES_OTEL_REF=0180c5e63b9d035ee0754d9a0d75c3499a8def26
ARG OTEL_PYTHON_VERSION=1.44.0
ARG PYYAML_VERSION=6.0.3

RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends gh git rsync; \
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
  # Install the reviewed hermes-otel source and OTel dependencies at image
  # build time. Runtime containers never install or mutate plugin code.
  . /opt/hermes/.venv/bin/activate && uv pip install --no-cache-dir \
    "opentelemetry-api==${OTEL_PYTHON_VERSION}" \
    "opentelemetry-sdk==${OTEL_PYTHON_VERSION}" \
    "opentelemetry-exporter-otlp-proto-http==${OTEL_PYTHON_VERSION}" \
    "PyYAML==${PYYAML_VERSION}"; \
  git clone --filter=blob:none https://github.com/briancaffey/hermes-otel.git \
    /opt/hermes/plugins/hermes_otel; \
  git -C /opt/hermes/plugins/hermes_otel checkout --detach "${HERMES_OTEL_REF}"; \
  test "$(git -C /opt/hermes/plugins/hermes_otel rev-parse HEAD)" = "${HERMES_OTEL_REF}"; \
  rm -rf /opt/hermes/plugins/hermes_otel/.git; \
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

