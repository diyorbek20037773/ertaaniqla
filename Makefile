# Erta aniqla — developer entry points (spec §15). Works on Linux/macOS/Git Bash (Windows).
SHELL := bash
.DEFAULT_GOAL := help

COMPOSE_DEV  := docker compose -f compose.yml -f compose.dev.yml
COMPOSE_PROD := docker compose -f compose.yml -f compose.prod.yml
UV           := uv run
MANAGE       := $(UV) python manage.py
ENV          ?= staging
DATE         ?= $(shell date +%Y-%m-%d)
SERVICE      ?= web

.PHONY: help dev down shell migrate makemigrations seed messages compilemessages \
        lint fmt type test check translations e2e lighthouse pa11y build deploy backup restore logs \
        install frontend frontend-watch superuser

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## uv sync + npm ci + playwright browsers
	uv sync
	npm ci
	$(UV) playwright install chromium

dev: ## docker compose up (dev overrides) + tailwind/esbuild watch
	$(COMPOSE_DEV) up -d --build
	npm run watch

down: ## stop dev stack
	$(COMPOSE_DEV) down

shell: ## django shell_plus
	$(MANAGE) shell_plus

superuser: ## create a CMS superuser
	$(MANAGE) createsuperuser

migrate: ## apply migrations
	$(MANAGE) migrate --noinput

makemigrations: ## create migrations
	$(MANAGE) makemigrations

seed: ## seed the full TZ page tree (uz+ru) and sample institutions
	$(MANAGE) seed_content --lang uz,ru
	$(MANAGE) import_institutions data/institutions.sample.csv

messages: ## extract translatable strings
	$(MANAGE) makemessages -l uz -l ru --ignore=.venv --ignore=node_modules --ignore=staticfiles --no-location
	$(MANAGE) makemessages -d djangojs -l uz -l ru --ignore=.venv --ignore=node_modules --ignore=staticfiles --ignore=static/dist --no-location

compilemessages: ## compile .po → .mo
	$(MANAGE) compilemessages --ignore=.venv --ignore=node_modules

lint: ## ruff check + format check
	$(UV) ruff check .
	$(UV) ruff format --check .

fmt: ## ruff format + autofix
	$(UV) ruff format .
	$(UV) ruff check --fix .

type: ## mypy
	$(UV) mypy

test: ## pytest with coverage gate
	$(UV) pytest --cov --cov-report=term-missing --cov-report=xml

translations: ## fail on untranslated uz/ru strings
	$(UV) python scripts/check_translations.py

check: lint type test translations ## lint + type + test + translations

e2e: ## playwright e2e (needs a running server at $${E2E_BASE_URL:-http://localhost:8000})
	$(UV) pytest tests/e2e -m e2e --browser chromium

lighthouse: ## lighthouse-ci against local (.lighthouseci/ reports)
	npx --yes @lhci/cli@0.14 autorun --config=lighthouserc.json

pa11y: ## pa11y-ci (WCAG 2.1 AA) against local :8001 (.pa11yci.json)
	npx pa11y-ci

frontend: ## build tailwind + js once
	npm run build

frontend-watch: ## watch tailwind + js
	npm run watch

build: ## docker build (multi-stage, includes tailwind)
	docker build -f docker/web/Dockerfile -t ertaaniqla/web:local --build-arg APP_RELEASE=$$(git rev-parse --short HEAD) .

deploy: ## deploy ENV=staging|prod over ssh (see docs/RUNBOOK.md)
	bash docker/scripts/deploy.sh $(ENV)

backup: ## run a backup now
	$(COMPOSE_PROD) run --rm backup /scripts/backup.sh

restore: ## restore DATE=YYYY-MM-DD (see docs/RUNBOOK.md)
	$(COMPOSE_PROD) run --rm backup /scripts/restore.sh $(DATE)

logs: ## tail logs SERVICE=web
	$(COMPOSE_DEV) logs -f --tail=200 $(SERVICE)
