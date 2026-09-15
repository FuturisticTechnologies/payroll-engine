# ---------------------------------------------------------------------------
# PayrollFuturistic — developer shortcuts
# ---------------------------------------------------------------------------

.DEFAULT_GOAL := help

.PHONY: help up down restart logs ps \
        backend-sh backend-test backend-lint migrate revision \
        frontend-sh frontend-test frontend-lint \
        lint test clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------- Stack ----------
up: ## Build and start the full stack
	docker compose up --build

down: ## Stop the stack
	docker compose down

restart: ## Restart the stack
	docker compose restart

logs: ## Tail logs from all services
	docker compose logs -f --tail=200

ps: ## List running services
	docker compose ps

# ---------- Backend ----------
backend-sh: ## Shell into the backend container
	docker compose exec backend sh

backend-test: ## Run backend tests inside the container
	docker compose exec backend pytest -q

backend-lint: ## Ruff (blocking) + mypy (non-blocking), as CI runs them
	docker compose exec backend sh -c "ruff check app tests && { mypy app || echo 'mypy reported errors (non-blocking, as in CI)'; }"

migrate: ## Apply database migrations
	docker compose exec backend alembic upgrade head

revision: ## Create a new auto-generated migration (msg=...)
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# ---------- Frontend ----------
frontend-sh: ## Shell into the frontend container
	docker compose exec frontend sh

frontend-test: ## Run frontend unit tests
	docker compose exec frontend npm test -- --watch=false --browsers=ChromeHeadlessNoSandbox

frontend-lint: ## No frontend linter is configured
	@echo "No frontend linter configured: angular.json has no ESLint builder and CI does not lint the frontend."

# ---------- Aggregate ----------
lint: backend-lint frontend-lint ## Lint everything

test: backend-test frontend-test ## Test everything

clean: ## Stop stack and remove volumes
	docker compose down -v
