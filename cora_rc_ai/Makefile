.PHONY: install db-up db-down db-migrate dev-api dev-agentic dev-frontend dev eval clean

install:
	uv pip install -e .

db-up:
	docker run --name cora-postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cora_db -d pgvector/pgvector:pg16

db-down:
	docker stop cora-postgres || true
	docker rm cora-postgres || true

db-migrate:
	psql -h localhost -p 5432 -U postgres -d cora_db -f data-layer/postgres/schema.sql

dev-api:
	uv run python -m cora_rc_ai.backend_api.main

dev-agentic:
	uv run python -m cora_rc_ai.backend_agentic.main

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting all dev servers..."
	# Normally run concurrently using a tool like concurrently or in separate terms.
	# We run them using python commands or background tasks.

eval:
	python evaluation/ragas_eval.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
