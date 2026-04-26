ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
FROM ${HERMES_BASE_IMAGE}

ARG HERMES_UID=1000
ARG HERMES_GID=1000

RUN set -eux; \
    if [ "$HERMES_GID" != "$(id -g hermes)" ]; then \
      groupmod -o -g "$HERMES_GID" hermes; \
    fi; \
    if [ "$HERMES_UID" != "$(id -u hermes)" ]; then \
      usermod -u "$HERMES_UID" hermes; \
    fi; \
    mkdir -p /opt/data; \
    chown -R hermes:hermes /opt/data
