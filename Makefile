# Company Leave Management System - Docker Operations Makefile
# Simplifies common Docker operations for development and deployment

.PHONY: help build deploy start stop restart logs status clean backup restore shell migrate collectstatic createsuperuser

# Default target
.DEFAULT_GOAL := help

# Application configuration
APP_NAME = company-leave-system
COMPOSE_FILE = docker-compose.yml
DOCKER_IMAGE = $(APP_NAME):latest

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Company Leave Management System - Docker Operations$(NC)"
	@echo "$(YELLOW)Available commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Build and deployment commands
build: ## Build Docker image
	@echo "$(YELLOW)Building Docker image...$(NC)"
	docker-compose -f $(COMPOSE_FILE) build

deploy: ## Deploy application (build + start + setup)
	@echo "$(YELLOW)Deploying application...$(NC)"
	@./docker-deploy.sh deploy

quick-deploy: ## Quick deployment without checks
	@echo "$(YELLOW)Quick deploying application...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d

# Container management
start: ## Start containers
	@echo "$(YELLOW)Starting containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) start

stop: ## Stop containers
	@echo "$(YELLOW)Stopping containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) stop

restart: ## Restart containers
	@echo "$(YELLOW)Restarting containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) restart

down: ## Stop and remove containers
	@echo "$(YELLOW)Stopping and removing containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down

# Monitoring and debugging
logs: ## Show application logs
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-web: ## Show web container logs only
	docker-compose -f $(COMPOSE_FILE) logs -f web

status: ## Show container status
	@echo "$(YELLOW)Container Status:$(NC)"
	docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(YELLOW)Resource Usage:$(NC)"
	docker stats --no-stream

health: ## Check application health
	@echo "$(YELLOW)Checking application health...$(NC)"
	@curl -f http://localhost:8082/admin/login/ >/dev/null 2>&1 && \
		echo "$(GREEN)✓ Application is healthy$(NC)" || \
		echo "$(RED)✗ Application is not responding$(NC)"

# Database operations
migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py migrate

makemigrations: ## Create new migrations
	@echo "$(YELLOW)Creating new migrations...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py makemigrations

showmigrations: ## Show migration status
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py showmigrations

# Data management
backup: ## Create database backup
	@echo "$(YELLOW)Creating database backup...$(NC)"
	@./docker-deploy.sh backup

restore: ## Restore from backup
	@echo "$(YELLOW)Restoring from backup...$(NC)"
	@./docker-deploy.sh restore

loaddata: ## Load initial data
	@echo "$(YELLOW)Loading initial data...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python load_csv_data.py

dumpdata: ## Export data to JSON
	@echo "$(YELLOW)Exporting data to JSON...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py dumpdata > data_export.json

# Django management
collectstatic: ## Collect static files
	@echo "$(YELLOW)Collecting static files...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py collectstatic --noinput

createsuperuser: ## Create Django superuser
	@echo "$(YELLOW)Creating superuser...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py createsuperuser

shell: ## Access Django shell
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py shell

shell-bash: ## Access container bash shell
	docker-compose -f $(COMPOSE_FILE) exec web bash

# Development tools
test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py test

check: ## Run Django system checks
	@echo "$(YELLOW)Running Django system checks...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python manage.py check

lint: ## Run code linting (if pylint is available)
	@echo "$(YELLOW)Running code linting...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec web python -m pylint leave/ || echo "Pylint not available"

# Production operations
prod-deploy: ## Deploy with production profile
	@echo "$(YELLOW)Deploying with production profile...$(NC)"
	COMPOSE_PROFILES=production docker-compose -f $(COMPOSE_FILE) up -d

prod-logs: ## Show production logs
	COMPOSE_PROFILES=production docker-compose -f $(COMPOSE_FILE) logs -f

ssl-check: ## Check SSL certificate
	@echo "$(YELLOW)Checking SSL certificate...$(NC)"
	@openssl x509 -in nginx/ssl/cert.pem -text -noout 2>/dev/null || \
		echo "$(RED)SSL certificate not found at nginx/ssl/cert.pem$(NC)"

# Cleanup operations
clean: ## Remove containers and volumes
	@echo "$(RED)Warning: This will remove all containers and data!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] && \
		./docker-deploy.sh clean

clean-images: ## Remove unused Docker images
	@echo "$(YELLOW)Cleaning unused Docker images...$(NC)"
	docker image prune -f

clean-all: ## Complete cleanup (containers, volumes, images)
	@echo "$(RED)Warning: This will remove everything!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] && \
		docker-compose -f $(COMPOSE_FILE) down -v --rmi all

# Environment management
env-setup: ## Setup environment file
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env from template...$(NC)"; \
		cp .env.docker .env; \
		echo "$(GREEN)✓ Environment file created. Please edit .env with your settings.$(NC)"; \
	else \
		echo "$(GREEN)✓ Environment file already exists.$(NC)"; \
	fi

env-check: ## Check environment configuration
	@echo "$(YELLOW)Environment Configuration:$(NC)"
	@if [ -f .env ]; then \
		echo "$(GREEN)✓ .env file exists$(NC)"; \
		grep -E "^DJANGO_|^EMAIL_|^COMPANY_" .env | head -5; \
	else \
		echo "$(RED)✗ .env file not found$(NC)"; \
	fi

# Data directory management
data-setup: ## Setup data directories
	@echo "$(YELLOW)Setting up data directories...$(NC)"
	mkdir -p data/{db,media,logs} backups
	chmod 755 data backups
	@echo "$(GREEN)✓ Data directories created$(NC)"

data-permissions: ## Fix data directory permissions
	@echo "$(YELLOW)Fixing data directory permissions...$(NC)"
	sudo chown -R $$USER:$$USER data/ backups/
	chmod -R 755 data/ backups/
	@echo "$(GREEN)✓ Permissions fixed$(NC)"

# Information commands
info: ## Show system information
	@echo "$(YELLOW)System Information:$(NC)"
	@echo "Docker version: $$(docker --version)"
	@echo "Docker Compose version: $$(docker-compose --version)"
	@echo "Application status: $$(docker-compose -f $(COMPOSE_FILE) ps --services | wc -l) services defined"
	@echo "Data directory size: $$(du -sh data/ 2>/dev/null || echo 'No data directory')"
	@echo "Backup count: $$(ls backups/*.sqlite3 2>/dev/null | wc -l) backups available"

ports: ## Show port usage
	@echo "$(YELLOW)Port Usage:$(NC)"
	@echo "Application: http://localhost:8082"
	@echo "Admin Panel: http://localhost:8082/admin/"
	@echo "Nginx (if enabled): http://localhost:80"
	@netstat -tlnp 2>/dev/null | grep -E ":8082|:80|:443" || echo "Ports not in use"

# Quick actions
quick-restart: stop start ## Quick restart (stop + start)

quick-logs: ## Show last 50 log lines
	docker-compose -f $(COMPOSE_FILE) logs --tail=50

quick-backup: ## Quick backup with timestamp
	@timestamp=$$(date +%Y%m%d_%H%M%S) && \
		echo "$(YELLOW)Creating quick backup: backup_$$timestamp$(NC)" && \
		./docker-deploy.sh backup

# Development shortcuts
dev: env-setup data-setup build deploy ## Complete development setup

reset: down clean-images dev ## Reset everything and redeploy

update: ## Update and redeploy
	@echo "$(YELLOW)Updating application...$(NC)"
	git pull origin main
	docker-compose -f $(COMPOSE_FILE) build
	docker-compose -f $(COMPOSE_FILE) up -d