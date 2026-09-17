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
        install frontend frontend-watch superuser nginx-test compose-check restore-test ops-check \
        prod-up prod-down tls-init maintenance-on maintenance-off ci-local sonar sonar-up

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

ci-local: check frontend build ## pre-push gate: what CI runs first (check + tailwind + docker image)
	@echo "ci-local OK — safe to git push"

sonar: ## SonarQube scan from this machine (SONAR_HOST_URL, SONAR_TOKEN; run make test first for coverage)
	docker run --rm -e SONAR_HOST_URL -e SONAR_TOKEN -v "$$(pwd -W 2>/dev/null || pwd):/usr/src" sonarsource/sonar-scanner-cli:11 -Dsonar.projectVersion=$$(git rev-parse --short HEAD)

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

deploy: ## deploy ENV=staging|prod over ssh (DEPLOY_HOST, IMAGE_BASE, TAG; see docs/RUNBOOK.md)
	bash docker/scripts/deploy.sh $(ENV) $(TAG)

backup: ## run a backup now (prod compose)
	$(COMPOSE_PROD) run --rm backup /scripts/backup.sh

restore: ## restore DATE=YYYY-MM-DD|latest into the live DB — disaster path, see docs/RUNBOOK.md
	$(COMPOSE_PROD) run --rm backup /scripts/restore.sh $(DATE)

restore-test: ## restore the latest dump into a scratch DB, count pages, drop it
	$(COMPOSE_PROD) run --rm backup /scripts/restore_test.sh

nginx-test: ## nginx -t for docker/nginx inside the nginx image
	bash docker/scripts/nginx_test.sh

compose-check: ## validate compose.yml + compose.prod.yml (+ profiles) + compose.sonarqube.yml
	$(COMPOSE_PROD) --profile monitoring --profile clamav config --quiet && echo "compose config OK"
	docker compose -f compose.sonarqube.yml config --quiet && echo "sonarqube compose config OK"

ops-check: nginx-test compose-check ## M6 gate: nginx -t, compose config, prometheus/alertmanager configs
	docker run --rm -v "$$(pwd -W 2>/dev/null || pwd)/docker/monitoring:/m:ro" --entrypoint sh prom/prometheus:v2.55.1 -c 'sed "s|__METRICS_USER__|u|;s|__METRICS_PASS__|p|;s|__DOMAIN__|example.uz|g" /m/prometheus.yml > /tmp/p.yml && cp /m/alert_rules.yml /tmp/ && sed -i "s|/etc/prometheus/alert_rules.yml|/tmp/alert_rules.yml|" /tmp/p.yml && promtool check config /tmp/p.yml'
	docker run --rm -v "$$(pwd -W 2>/dev/null || pwd)/docker/monitoring:/m:ro" --entrypoint sh prom/alertmanager:v0.27.0 -c 'sed "s|__TELEGRAM_BOT_TOKEN__|1:a|;s|__TELEGRAM_ALERT_CHAT_ID__|1|" /m/alertmanager.yml > /tmp/a.yml && amtool check-config /tmp/a.yml'

prod-up: ## start the production stack on this host (+ monitoring profile)
	$(COMPOSE_PROD) --profile monitoring up -d

sonar-up: ## start self-hosted SonarQube on this host (separate compose project, ADR-0005)
	docker compose -p ertaaniqla-sonarqube --env-file .env -f compose.sonarqube.yml up -d

prod-down: ## stop the production stack (volumes are kept)
	$(COMPOSE_PROD) --profile monitoring down

tls-init: ## first certificate: DOMAIN=... DOMAIN_ALT="..." LETSENCRYPT_EMAIL=... make tls-init
	COMPOSE="$(COMPOSE_PROD)" bash docker/scripts/init_letsencrypt.sh

maintenance-on: ## serve the maintenance page (nginx flag)
	touch docker/nginx/maintenance/maintenance.flag

maintenance-off: ## back to normal
	rm -f docker/nginx/maintenance/maintenance.flag

logs: ## tail logs SERVICE=web
	$(COMPOSE_DEV) logs -f --tail=200 $(SERVICE)
