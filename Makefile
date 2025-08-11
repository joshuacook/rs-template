.PHONY: help test test-unit test-integration test-gateway test-api test-ai docker-up docker-down clean setup

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Testing Commands
test: test-unit ## Run all unit tests

test-unit: ## Run unit tests for all services
	@echo "Running unit tests for all services..."
	@echo "\n=== Gateway Service Tests ==="
	@cd services/gateway && uv run pytest tests/unit/ -v
	@echo "\n=== API Service Tests ==="
	@cd services/api && uv run pytest tests/unit/ -v
	@echo "\n=== AI Service Tests ==="
	@cd services/ai && uv run pytest tests/unit/ -v

test-gateway: ## Run gateway service unit tests
	@cd services/gateway && uv run pytest tests/unit/ -v

test-api: ## Run API service unit tests
	@cd services/api && uv run pytest tests/unit/ -v

test-ai: ## Run AI service unit tests
	@cd services/ai && uv run pytest tests/unit/ -v

test-integration: docker-up ## Run integration tests against Docker Compose
	@echo "\n=== Integration Tests ==="
	@cd tools/test-runner && python run_tests.py local -v

test-summary: ## Show test summary for all services
	@echo "=== Test Summary ==="
	@echo "\nGateway Service:"
	@cd services/gateway && uv run pytest tests/unit/ -q --tb=no || true
	@echo "\nAPI Service:"
	@cd services/api && uv run pytest tests/unit/ -q --tb=no || true
	@echo "\nAI Service:"
	@cd services/ai && uv run pytest tests/unit/ -q --tb=no || true

# Docker Commands
run-local: docker-up ## Alias for docker-up

docker-up: ## Start all services with Docker Compose
	docker-compose up --build -d
	@echo "Services started. View logs with: make docker-logs"

docker-down: ## Stop all Docker Compose services
	docker-compose down

stop: docker-down ## Alias for docker-down

docker-logs: ## Show Docker Compose logs
	docker-compose logs -f

clean: ## Clean up Docker containers, images and Python caches
	docker-compose down -v
	docker system prune -f
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete

# Development Commands
dev-gateway: ## Run gateway service locally with hot reload
	cd services/gateway && uvicorn main:app --reload --port 8080

dev-api: ## Run API service locally with hot reload
	cd services/api && uvicorn main:app --reload --port 8081

dev-ai: ## Run AI service locally with hot reload
	cd services/ai && uvicorn main:app --reload --port 8082

# Setup Commands
setup: ## Set up all services with UV
	@echo "Setting up UV for all services..."
	@cd services/gateway && uv sync
	@cd services/api && uv sync
	@cd services/ai && uv sync
	@echo "Setup complete!"

# Deployment Commands
deploy-staging: ## Deploy to staging (push to staging branch)
	git push origin staging

deploy-prod: ## Deploy to production (push to main branch)
	git push origin main