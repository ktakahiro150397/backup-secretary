ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
FROM ${HERMES_BASE_IMAGE}

USER root

ARG HERMES_UID=1000
ARG HERMES_GID=1000

RUN set -eux; \
    current_uid="$(id -u hermes)"; \
    current_gid="$(id -g hermes)"; \
    if [ "$current_gid" != "$HERMES_GID" ]; then \
      groupmod -o -g "$HERMES_GID" hermes; \
    fi; \
    if [ "$current_uid" != "$HERMES_UID" ]; then \
      usermod -o -u "$HERMES_UID" hermes; \
    fi; \
    chown -R hermes:hermes /opt/hermes /opt/data

USER hermes
