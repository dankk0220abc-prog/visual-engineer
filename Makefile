SHELL := /bin/sh
.DEFAULT_GOAL := help

TEST_DATABASE_URL ?= postgresql+psycopg://visualengineer:visualengineer-test-local@localhost:55433/visualengineer_test
WORKSPACE_FIXTURE_REPOSITORY_PATH ?= $(CURDIR)/.runtime/workspace-fixture

.PHONY: help bootstrap db-up db-down migrate contracts contracts-check format format-check format-check-api format-check-web lint lint-api lint-web typecheck typecheck-api typecheck-web test test-api test-api-direct test-runner test-web build build-web e2e eval verify platform-up platform-down platform-logs runner-status runner-smoke runner-chaos-check workspace-smoke workspace-chaos-check workspace-security-check workspace-security-audit workspace-security-repair-check phase4-findings-check source-invariance-check validation-security-check up down logs migration-check docker-config security-check customer0-up customer0-down customer0-readonly-case

help:
	@echo "VisualEngineer Phase 5 commands: bootstrap platform-up validation-security-check verify platform-down"

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
	uv run ruff format apps/api apps/runner packages/runner-protocol scripts
	pnpm format

format-check-api:
	uv run ruff format --check apps/api apps/runner packages/runner-protocol scripts

format-check-web:
	pnpm format:check

format-check: format-check-api format-check-web

lint-api:
	uv run ruff check apps/api apps/runner packages/runner-protocol scripts

lint-web:
	pnpm lint

lint: lint-api lint-web

typecheck-api:
	uv run mypy

typecheck-web:
	pnpm typecheck

typecheck: typecheck-api typecheck-web

test-api:
	./scripts/run-backend-tests.sh

test-api-direct:
	uv run pytest

test-runner:
	uv run pytest apps/runner/tests packages/runner-protocol/tests --no-cov -q

test-web:
	pnpm test

test: test-api test-web

build-web:
	pnpm build

build: build-web

docker-config:
	docker compose config --quiet
	docker compose --profile test config --quiet
	WORKSPACE_FIXTURE_REPOSITORY_PATH=/tmp/visualengineer-workspace docker compose -f compose.yaml -f infra/compose.workspace.yaml config --quiet
	E2E_REPOSITORY_PATH=/tmp/visualengineer-synthetic WORKSPACE_FIXTURE_REPOSITORY_PATH=/tmp/visualengineer-workspace docker compose -f compose.yaml -f infra/compose.workspace.yaml -f infra/compose.e2e.yaml config --quiet
	CUSTOMER0_REPOSITORY_PATH=/tmp/visualengineer-customer0 docker compose -f compose.yaml -f infra/compose.customer0.yaml config --quiet

security-check:
	./scripts/check-secrets.sh
	uv run python scripts/check_runner_security.py
	PYTHONPATH="apps/runner/src:packages/runner-protocol/src" uv run python scripts/check_phase4_findings.py
	uv run pytest apps/api/tests/test_repository_scanner.py --no-cov -q
	./scripts/run-runner-security-tests.sh

workspace-security-check:
	uv run pytest apps/runner/tests/test_workspace_tools.py packages/runner-protocol/tests --no-cov -q
	uv run python scripts/check_workspace_security.py

validation-security-check:
	uv run python scripts/check_validation_sandbox.py

workspace-security-audit:
	uv run pytest apps/runner/tests/security_audit --no-cov -q

phase4-findings-check:
	PYTHONPATH="apps/runner/src:packages/runner-protocol/src" uv run python scripts/check_phase4_findings.py
	uv run pytest apps/runner/tests/security_audit --no-cov -q

source-invariance-check:
	PYTHONPATH="apps/runner/src:packages/runner-protocol/src" uv run python scripts/check_source_invariance.py

workspace-security-repair-check:
	./scripts/run-phase4-security-repair-check.sh

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
	$(MAKE) phase4-findings-check
	$(MAKE) source-invariance-check
	$(MAKE) workspace-security-repair-check
	$(MAKE) e2e
	$(MAKE) workspace-chaos-check
	$(MAKE) workspace-security-check
	$(MAKE) validation-security-check
	$(MAKE) security-check
	$(MAKE) eval
	git diff --check

platform-up:
	uv run python scripts/create_workspace_fixture.py
	uv run python scripts/ensure_runner_bootstrap.py
	WORKSPACE_FIXTURE_REPOSITORY_PATH="$(WORKSPACE_FIXTURE_REPOSITORY_PATH)" docker compose --env-file .env.runner.local -f compose.yaml -f infra/compose.workspace.yaml up -d --build --wait db api web runner
	$(MAKE) runner-status
	WORKSPACE_API_BASE_URL="http://127.0.0.1:$${API_PUBLISHED_PORT:-8000}" WORKSPACE_DATABASE_URL="postgresql+psycopg://$${POSTGRES_USER:-visualengineer}:$${POSTGRES_PASSWORD:-visualengineer-local}@127.0.0.1:$${POSTGRES_PUBLISHED_PORT:-5432}/$${POSTGRES_DB:-visualengineer}" uv run python scripts/seed_workspace_e2e.py
	@echo "VisualEngineer Web Console: http://127.0.0.1:$${WEB_PUBLISHED_PORT:-3000}"
	@echo "Workspace Console: http://127.0.0.1:$${WEB_PUBLISHED_PORT:-3000}/workspaces"

platform-down:
	WORKSPACE_FIXTURE_REPOSITORY_PATH="$(WORKSPACE_FIXTURE_REPOSITORY_PATH)" docker compose -f compose.yaml -f infra/compose.workspace.yaml down

platform-logs:
	WORKSPACE_FIXTURE_REPOSITORY_PATH="$(WORKSPACE_FIXTURE_REPOSITORY_PATH)" docker compose -f compose.yaml -f infra/compose.workspace.yaml logs --tail=200 -f api web runner db

runner-status:
	uv run python scripts/runner_status.py

runner-smoke: platform-up
	uv run python scripts/runner_smoke.py

runner-chaos-check:
	./scripts/run-runner-chaos-check.sh

workspace-smoke: platform-up
	uv run python scripts/workspace_smoke.py

workspace-chaos-check:
	./scripts/run-workspace-chaos-check.sh

up: platform-up

down: platform-down

logs: platform-logs

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
