COMPOSE ?= docker compose
OV_CLI ?= /app/.venv/bin/ov

.PHONY: up down ps logs pull restart restart-main restart-owashota patch-hermes-openviking ov ov-tui ov-config ov-init ov-doctor ov-root-config ov-provision-user ov-regenerate-key setup-main setup-owashota hermes-main hermes-owashota

up:
	$(COMPOSE) up -d openviking hermes-main hermes-owashota

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f openviking hermes-main hermes-owashota

pull:
	$(COMPOSE) pull openviking hermes-main hermes-owashota

restart:
	$(COMPOSE) restart hermes-main hermes-owashota

restart-main:
	$(COMPOSE) restart hermes-main

restart-owashota:
	$(COMPOSE) restart hermes-owashota

patch-hermes-openviking:
	$(COMPOSE) cp hermes-owashota:/opt/hermes/plugins/memory/openviking/__init__.py /tmp/hermes-openviking.py
	python3 scripts/patch_hermes_openviking_browse.py /tmp/hermes-openviking.py
	$(COMPOSE) cp /tmp/hermes-openviking.py hermes-main:/opt/hermes/plugins/memory/openviking/__init__.py
	$(COMPOSE) cp /tmp/hermes-openviking.py hermes-owashota:/opt/hermes/plugins/memory/openviking/__init__.py
	$(COMPOSE) restart hermes-main hermes-owashota

ov:
	$(COMPOSE) exec openviking $(OV_CLI) $(ARGS)

ov-tui:
	$(COMPOSE) exec openviking $(OV_CLI) tui

ov-config:
	$(COMPOSE) exec openviking $(OV_CLI) config

ov-init:
	$(COMPOSE) up -d openviking
	$(COMPOSE) exec openviking openviking-server init

ov-doctor:
	$(COMPOSE) exec openviking openviking-server doctor
	curl -fsS http://127.0.0.1:$${OPENVIKING_PORT:-1933}/health

ov-root-config:
	$(COMPOSE) exec openviking $(OV_CLI) config add custom --name root-admin --url http://127.0.0.1:1933 --root-api-key-env OPENVIKING_ROOT_API_KEY --account root --user root --activate --force

ov-provision-user: ov-root-config
	@test -n "$(ACCOUNT)" -a -n "$(NAME)" || (echo 'usage: make ov-provision-user ACCOUNT=<account> NAME=<user>' >&2; exit 2)
	@printf '%s' "$(ACCOUNT)" | grep -Eq '^[a-z0-9][a-z0-9_-]*$$' || (echo 'ACCOUNT must match ^[a-z0-9][a-z0-9_-]*$$' >&2; exit 2)
	@printf '%s' "$(NAME)" | grep -Eq '^[a-z0-9][a-z0-9_-]*$$' || (echo 'NAME must match ^[a-z0-9][a-z0-9_-]*$$' >&2; exit 2)
	$(COMPOSE) exec openviking $(OV_CLI) admin register-user "$(ACCOUNT)" "$(NAME)" --role user --sudo

ov-regenerate-key:
	@test -n "$(ACCOUNT)" -a -n "$(NAME)" || (echo 'usage: make ov-regenerate-key ACCOUNT=<account> NAME=<user>' >&2; exit 2)
	@printf '%s' "$(ACCOUNT)" | grep -Eq '^[a-z0-9][a-z0-9_-]*$$' || (echo 'ACCOUNT must match ^[a-z0-9][a-z0-9_-]*$$' >&2; exit 2)
	@printf '%s' "$(NAME)" | grep -Eq '^[a-z0-9][a-z0-9_-]*$$' || (echo 'NAME must match ^[a-z0-9][a-z0-9_-]*$$' >&2; exit 2)
	@echo 'WARNING: this invalidates the current API key.'
	$(COMPOSE) exec openviking $(OV_CLI) admin regenerate-key "$(ACCOUNT)" "$(NAME)" --sudo

setup-main:
	$(COMPOSE) --profile setup run --rm setup-main

setup-owashota:
	$(COMPOSE) --profile setup run --rm setup-owashota

hermes-main:
	$(COMPOSE) run --rm hermes-main chat

hermes-owashota:
	$(COMPOSE) run --rm hermes-owashota chat
