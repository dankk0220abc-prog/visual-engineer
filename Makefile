SHELL := /bin/sh
.DEFAULT_GOAL := help

TEST_DATABASE_URL ?= postgresql+psycopg://visualengineer:visualengineer-test-local@localhost:55433/visualengineer_test

.PHONY: help bootstrap db-up db-down migrate contracts contracts-check format format-check format-check-api format-check-web lint lint-api lint-web typecheck typecheck-api typecheck-web test test-api test-api-direct test-web build build-web e2e verify up down logs migration-check docker-config security-check

help:
	@echo "VisualEngineer Foundation commands: bootstrap db-up migrate up verify down"

bootstrap:
	uv sync --frozen
	pnpm install --frozen-lockfile

db-up:
	docker compose up -d --wait db

db-down:
	docker compose stop db

migrate:
	uv run alembic -c apps/api/alembic.ini upgrade head

contracts:
	pnpm --filter @visual-engineer/api-contract generate

contracts-check:
	./scripts/check-contract-drift.sh

format:
	uv run ruff format apps/api scripts
	pnpm format

format-check-api:
	uv run ruff format --check apps/api scripts

format-check-web:
	pnpm format:check

format-check: format-check-api format-check-web

lint-api:
	uv run ruff check apps/api scripts

lint-web:
	pnpm lint

lint: lint-api lint-web

typecheck-api:
	uv run mypy apps/api/src apps/api/tests

typecheck-web:
	pnpm typecheck

typecheck: typecheck-api typecheck-web

test-api:
	./scripts/run-backend-tests.sh

test-api-direct:
	uv run pytest

test-web:
	pnpm test

test: test-api test-web

build-web:
	pnpm build

build: build-web

docker-config:
	docker compose config --quiet
	docker compose --profile test config --quiet

security-check:
	./scripts/check-secrets.sh

migration-check:
	./scripts/run-migration-check.sh

e2e:
	./scripts/run-e2e.sh

verify:
	$(MAKE) contracts-check
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) build
	$(MAKE) docker-config
	$(MAKE) migration-check
	$(MAKE) e2e
	$(MAKE) security-check
	git diff --check

up:
	docker compose up -d --build --wait db api web

down:
	docker compose down

logs:
	docker compose logs --tail=200 -f api web db
