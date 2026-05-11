FROM debian:stable-slim

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-noto-cjk \
        fonts-liberation \
        ca-certificates \
        dumb-init \
    ; \
    rm -rf /var/lib/apt/lists/*; \
    mkdir -p /data/chrome-profile

# Symlink for compatibility with OpenCLI expectations
RUN ln -sf /usr/bin/chromium /usr/bin/google-chrome || true

ENV CHROME_PROFILE_DIR=/data/chrome-profile
ENV CHROME_CDP_PORT=9222

EXPOSE 9222

ENTRYPOINT ["dumb-init", "--"]
CMD [ \
    "/bin/sh", "-c", \
    "exec chromium \
      --remote-debugging-port=${CHROME_CDP_PORT} \
      --user-data-dir=${CHROME_PROFILE_DIR} \
      --remote-allow-origins='*' \
      --no-sandbox \
      --disable-gpu \
      --disable-dev-shm-usage \
      --disable-background-timer-throttling \
      --disable-backgrounding-occluded-windows \
      --disable-renderer-backgrounding \
      --headless=new \
      --window-size=1920,1080 \
      about:blank" \
]
