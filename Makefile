# ATLAS developer shortcuts — Phase 1 / v0.1.0
.PHONY: help sync lint typecheck test web-install web-build web-dev compose-up compose-down compose-ps compose-logs migrate release-check

help:
	@echo "ATLAS v0.1.0 commands:"
	@echo "  make sync           - uv sync workspace"
	@echo "  make lint           - ruff check + format check"
	@echo "  make typecheck      - mypy"
	@echo "  make test           - pytest"
	@echo "  make web-install    - npm install in apps/web"
	@echo "  make web-build      - static Next.js export to apps/web/out"
	@echo "  make compose-up     - build web export + docker compose up --build -d"
	@echo "  make compose-down   - docker compose down"
	@echo "  make compose-ps     - docker compose ps"
	@echo "  make release-check  - lint + typecheck + test + web-build"

sync:
	uv sync

lint:
	uv run ruff check apps packages tests
	uv run ruff format --check apps packages tests

typecheck:
	uv run mypy

test:
	uv run pytest -q

web-install:
	cd apps/web && npm install

web-build: web-install
	cd apps/web && npm run build

compose-up: web-build
	docker compose up --build -d

compose-down:
	docker compose down

compose-ps:
	docker compose ps

compose-logs:
	docker compose logs --tail=100

migrate:
	cd apps/api && uv run alembic upgrade head

release-check: lint typecheck test web-build
	@echo "Release checks passed for ATLAS v0.1.0"
