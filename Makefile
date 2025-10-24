.PHONY: help up down restart logs build clean test install dev

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	@echo "Installing dependencies..."
	cd apps/api && pip install -r requirements.txt
	cd apps/web && npm install

up: ## Start all services
	@echo "Starting AutoBrain services..."
	docker-compose up -d
	@echo ""
	@echo "✅ Services started!"
	@echo "   Frontend: http://localhost:3000"
	@echo "   API: http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

down: ## Stop all services
	@echo "Stopping AutoBrain services..."
	docker-compose down

restart: ## Restart all services
	@echo "Restarting AutoBrain services..."
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API logs only
	docker-compose logs -f api

logs-web: ## View web logs only
	docker-compose logs -f web

build: ## Build Docker images
	@echo "Building Docker images..."
	docker-compose build

clean: ## Remove all containers, volumes, and images
	@echo "Cleaning up..."
	docker-compose down -v
	docker system prune -f

ps: ## Show status of all services
	docker-compose ps

test: ## Run tests
	@echo "Running API tests..."
	cd apps/api && pytest
	@echo "Running web tests..."
	cd apps/web && npm test

dev-api: ## Run API in development mode
	cd apps/api && uvicorn main:app --reload --port 8000

dev-web: ## Run web in development mode
	cd apps/web && npm run dev

shell-api: ## Open shell in API container
	docker-compose exec api /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U autobrain -d autobrain

backup-db: ## Backup database
	@echo "Backing up database..."
	docker-compose exec -T postgres pg_dump -U autobrain autobrain > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backed up"

restore-db: ## Restore database (Usage: make restore-db FILE=backup.sql)
	@echo "Restoring database from $(FILE)..."
	docker-compose exec -T postgres psql -U autobrain autobrain < $(FILE)
	@echo "✅ Database restored"

init: ## Initialize the project (first time setup)
	@echo "Initializing AutoBrain..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "⚠️  Please edit .env and add your API keys!"; \
	else \
		echo "✅ .env already exists"; \
	fi
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env and add your API keys"
	@echo "2. Run 'make up' to start services"
	@echo "3. Visit http://localhost:3000"

status: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | jq . || echo "❌ API not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "✅ Web is running" || echo "❌ Web not responding"
	@docker-compose ps
