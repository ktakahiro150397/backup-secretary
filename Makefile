COMPOSE ?= docker compose

.PHONY: up down logs ps build pull update deploy restart-main restart-owashota restart-all skills-sync openviking-init openviking-doctor cli-main

up:
	$(COMPOSE) up -d hermes-main hermes-owashota openviking searxng redis

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f hermes-main hermes-owashota openviking

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build --pull hermes-main hermes-owashota

pull:
	$(COMPOSE) pull openviking searxng redis

update:
	git pull --ff-only
	$(COMPOSE) --profile skills-sync run --rm --build skills-sync-main
	$(COMPOSE) --profile skills-sync run --rm --build skills-sync-owashota

# Use this after config.yaml, SOUL.md, Dockerfile, compose.yaml, or .env changes.
deploy:
	git pull --ff-only
	$(COMPOSE) pull openviking searxng redis
	$(COMPOSE) build --pull hermes-main hermes-owashota
	$(COMPOSE) up -d --remove-orphans hermes-main hermes-owashota openviking searxng redis
	$(COMPOSE) --profile skills-sync run --rm --build skills-sync-main
	$(COMPOSE) --profile skills-sync run --rm --build skills-sync-owashota
	$(COMPOSE) restart hermes-main hermes-owashota

restart-main:
	$(COMPOSE) restart hermes-main

restart-owashota:
	$(COMPOSE) restart hermes-owashota

restart-all:
	$(COMPOSE) restart hermes-main hermes-owashota

skills-sync:
	$(COMPOSE) --profile skills-sync run --rm --build skills-sync-main
	$(COMPOSE) --profile skills-sync run --rm --build skills-sync-owashota

openviking-init:
	$(COMPOSE) up -d openviking
	$(COMPOSE) exec openviking openviking-server init

openviking-doctor:
	$(COMPOSE) exec openviking openviking-server doctor
	curl -fsS http://127.0.0.1:$${OPENVIKING_PORT:-1933}/health

cli-main:
	$(COMPOSE) --profile cli run --rm cli-main bash -lc 'source /opt/hermes/.venv/bin/activate && exec hermes chat'
