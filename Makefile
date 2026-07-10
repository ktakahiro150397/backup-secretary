COMPOSE ?= docker compose

.PHONY: up down ps logs pull restart restart-main restart-owashota ov-init ov-doctor setup-main setup-owashota

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

ov-init:
	$(COMPOSE) up -d openviking
	$(COMPOSE) exec openviking openviking-server init

ov-doctor:
	$(COMPOSE) exec openviking openviking-server doctor
	curl -fsS http://127.0.0.1:$${OPENVIKING_PORT:-1933}/health

setup-main:
	$(COMPOSE) --profile setup run --rm setup-main

setup-owashota:
	$(COMPOSE) --profile setup run --rm setup-owashota
