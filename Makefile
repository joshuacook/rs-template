.PHONY: help run-local stop clean test deploy-staging deploy-production

help:
	@echo "Available commands:"
	@echo "  make run-local       - Run all services locally with docker-compose"
	@echo "  make stop           - Stop all local services"
	@echo "  make clean          - Clean up Docker containers and images"
	@echo "  make test           - Run all tests"
	@echo "  make deploy-staging - Deploy to staging (requires staging branch)"
	@echo "  make deploy-prod    - Deploy to production (requires main branch)"

run-local:
	docker-compose up --build

stop:
	docker-compose down

clean:
	docker-compose down -v
	docker system prune -f

test:
	@echo "Running Gateway tests..."
	cd services/gateway && python -m pytest tests/ -v
	@echo "Running API tests..."
	cd services/api && python -m pytest tests/ -v
	@echo "Running AI tests..."
	cd services/ai && python -m pytest tests/ -v

deploy-staging:
	git push origin staging

deploy-prod:
	git push origin main