.PHONY: help build up down logs shell test clean setup-db load-data

help:
	@echo "Available commands:"
	@echo "  make build      - Build all Docker containers"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make shell      - Open shell in backend container"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Remove containers and volumes"
	@echo "  make setup-db   - Initialize databases"
	@echo "  make load-data  - Load sample data"
	@echo "  make dev        - Start development environment"

# Build all containers
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"
	@echo "GraphQL: http://localhost:8000/graphql"
	@echo "Elasticsearch: http://localhost:9200"

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Open shell in backend container
shell:
	docker-compose exec backend bash

# Run tests
test:
	docker-compose exec backend pytest
	docker-compose exec frontend npm test

# Clean everything
clean:
	docker-compose down -v
	docker system prune -f

# Setup databases
setup-db:
	docker-compose exec backend python scripts/initialize_database.py

# Load sample data
load-data:
	docker-compose exec backend python scripts/sample_data_generator.py

# Development workflow
dev: build up setup-db load-data
	@echo "Development environment ready!"
	@echo "Visit http://localhost:3000 to see the application"

# Backend specific commands
backend-logs:
	docker-compose logs -f backend

backend-shell:
	docker-compose exec backend bash

backend-test:
	docker-compose exec backend pytest -v

# Frontend specific commands
frontend-logs:
	docker-compose logs -f frontend

frontend-shell:
	docker-compose exec frontend sh

frontend-test:
	docker-compose exec frontend npm test

# Database commands
db-shell:
	docker-compose exec postgres psql -U ohdsi -d ohdsi_db

es-health:
	curl -s http://localhost:9200/_cluster/health | python -m json.tool

redis-cli:
	docker-compose exec redis redis-cli

# Celery commands
celery-logs:
	docker-compose logs -f celery-worker celery-beat

celery-status:
	docker-compose exec celery-worker celery -A backend.app.workers inspect active

# Quick restart
restart: down up
	@echo "Services restarted!"

# Check status
status:
	@echo "Checking service status..."
	@docker-compose ps
	@echo ""
	@echo "Health checks:"
	@curl -s http://localhost:8000/health || echo "Backend: Not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend: OK" || echo "Frontend: Not responding"
	@curl -s http://localhost:9200/_cluster/health > /dev/null && echo "Elasticsearch: OK" || echo "Elasticsearch: Not responding"