.PHONY: bootstrap dev-api dev-web format lint typecheck test check build

bootstrap:
	cd services/inference && python3 -m venv .venv && .venv/bin/pip install -e ".[dev,runtime]"
	cd apps/web && npm ci

dev-api:
	cd services/inference && .venv/bin/uvicorn slatesignal.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

format:
	cd services/inference && .venv/bin/ruff format src tests migrations ../../scripts
	cd apps/web && npm run format

lint:
	cd services/inference && .venv/bin/ruff check src tests migrations ../../scripts
	cd apps/web && npm run lint

typecheck:
	cd services/inference && .venv/bin/mypy src
	cd apps/web && npm run typecheck

test:
	cd services/inference && .venv/bin/pytest --cov=slatesignal --cov-report=term-missing
	cd apps/web && npm test -- --coverage

check: lint typecheck test

build:
	cd apps/web && npm run build
