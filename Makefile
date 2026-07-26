SHELL := /bin/sh
.DEFAULT_GOAL := help

TEST_DATABASE_URL ?= postgresql+psycopg://visualengineer:visualengineer-test-local@localhost:55433/visualengineer_test

.PHONY: help bootstrap db-up db-down migrate contracts contracts-check format format-check format-check-api format-check-web lint lint-api lint-web typecheck typecheck-api typecheck-web test test-api test-api-direct test-web build build-web e2e eval verify up down logs migration-check docker-config security-check customer0-up customer0-down customer0-readonly-case

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
	E2E_REPOSITORY_PATH=/tmp/visualengineer-synthetic docker compose -f compose.yaml -f infra/compose.e2e.yaml config --quiet
	CUSTOMER0_REPOSITORY_PATH=/tmp/visualengineer-customer0 docker compose -f compose.yaml -f infra/compose.customer0.yaml config --quiet

security-check:
	./scripts/check-secrets.sh
	uv run pytest apps/api/tests/test_repository_scanner.py --no-cov -q

eval:
	uv run python scripts/validate_evals.py
	uv run pytest apps/api/tests/test_repository_scanner.py --no-cov -q

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
	$(MAKE) eval
	git diff --check

up:
	docker compose up -d --build --wait db api web

down:
	docker compose down

logs:
	docker compose logs --tail=200 -f api web db

customer0-up:
	@test -n "$(CUSTOMER0_REPOSITORY_PATH)" || (echo "Set CUSTOMER0_REPOSITORY_PATH explicitly." >&2; exit 1)
	POSTGRES_PUBLISHED_PORT="$${CUSTOMER0_DB_PORT:-15434}" \
	API_PUBLISHED_PORT="$${CUSTOMER0_API_PORT:-18001}" \
	WEB_PUBLISHED_PORT="$${CUSTOMER0_WEB_PORT:-13001}" \
	WEB_ORIGIN="http://127.0.0.1:$${CUSTOMER0_WEB_PORT:-13001},http://localhost:$${CUSTOMER0_WEB_PORT:-13001}" \
	NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:$${CUSTOMER0_API_PORT:-18001}" \
	CUSTOMER0_REPOSITORY_PATH="$(CUSTOMER0_REPOSITORY_PATH)" \
	docker compose -p visualengineer-customer0 -f compose.yaml -f infra/compose.customer0.yaml up -d --build --wait db api web

customer0-down:
	@test -n "$(CUSTOMER0_REPOSITORY_PATH)" || (echo "Set CUSTOMER0_REPOSITORY_PATH explicitly." >&2; exit 1)
	CUSTOMER0_REPOSITORY_PATH="$(CUSTOMER0_REPOSITORY_PATH)" \
	docker compose -p visualengineer-customer0 -f compose.yaml -f infra/compose.customer0.yaml down

customer0-readonly-case: customer0-up
	CUSTOMER0_API_BASE_URL="http://127.0.0.1:$${CUSTOMER0_API_PORT:-18001}" \
	CUSTOMER0_WEB_BASE_URL="http://127.0.0.1:$${CUSTOMER0_WEB_PORT:-13001}" \
	uv run python scripts/run_customer0_case.py
