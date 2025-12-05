.PHONY: help build up down logs shell test clean migrate init-db seed-db

help:
	@echo "Available commands:"
	@echo "  make build      - Build Docker images"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs"
	@echo "  make shell      - Open shell in app container"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Remove containers and volumes"
	@echo "  make migrate    - Create new migration"
	@echo "  make init-db    - Initialize database with migrations"
	@echo "  make seed-db    - Seed database with sample documents"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Qdrant: http://localhost:6333/dashboard"

down:
	docker-compose down

logs:
	docker-compose logs -f app

shell:
	docker-compose exec app /bin/bash

test:
	docker-compose exec app pytest -v --cov=medical_notes_processor tests/

clean:
	docker-compose down -v
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

migrate:
	docker-compose exec app alembic revision --autogenerate -m "$(msg)"

init-db:
	docker-compose exec app alembic upgrade head

seed-db:
	docker-compose exec app python -c "from scripts.seed_db import seed_documents; import asyncio; asyncio.run(seed_documents())"

# Local development (without Docker)
dev-install:
	uv sync --dev

dev-run:
	uv run uvicorn medical_notes_processor.main:app --reload

dev-test:
	uv run pytest -v --cov=medical_notes_processor tests/
