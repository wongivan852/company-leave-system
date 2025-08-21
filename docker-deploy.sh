#!/bin/bash

# Company Leave Management System - Docker Deployment Script
# Automated deployment for Linux Mint servers

set -e

# Configuration
APP_NAME="company-leave-system"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="./backups"
DATA_DIR="./data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed!"
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Create data directories
    mkdir -p "$DATA_DIR"/{db,media,logs}
    mkdir -p "$BACKUP_DIR"
    
    # Create environment file if it doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f ".env.docker" ]; then
            cp .env.docker "$ENV_FILE"
            print_success "Created $ENV_FILE from template"
        else
            print_warning "No environment template found. Creating basic $ENV_FILE"
            cat > "$ENV_FILE" << EOF
DJANGO_SECRET_KEY=django-insecure-change-this-in-production
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,*
EMAIL_HOST=smtp.yourcompany.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@yourcompany.com
EMAIL_HOST_PASSWORD=your-email-password
EOF
        fi
        
        print_warning "Please edit $ENV_FILE with your configuration before running the application"
    fi
    
    # Set proper permissions
    chmod 600 "$ENV_FILE"
    chmod 755 "$DATA_DIR"
    chmod 755 "$BACKUP_DIR"
    
    print_success "Environment setup completed!"
}

# Function to build and deploy
deploy() {
    print_status "Building and deploying application..."
    
    # Build the application
    docker-compose -f "$COMPOSE_FILE" build
    
    # Start the services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    print_success "Application deployed successfully!"
}

# Function to check deployment status
check_status() {
    print_status "Checking deployment status..."
    
    # Check if containers are running
    docker-compose -f "$COMPOSE_FILE" ps
    
    # Wait for application to be ready
    print_status "Waiting for application to be ready..."
    sleep 10
    
    # Check health
    if curl -f http://localhost:8082/admin/login/ &> /dev/null; then
        print_success "Application is healthy and accessible!"
        echo ""
        echo "🏢 Company Leave Management System is now running!"
        echo "📱 Web Interface: http://localhost:8082"
        echo "🛠️  Admin Panel: http://localhost:8082/admin/"
        echo "👤 Default Admin: admin / admin123"
        echo ""
        echo "📊 View logs: docker-compose logs -f"
        echo "🛑 Stop application: docker-compose down"
    else
        print_warning "Application may still be starting up. Check logs: docker-compose logs"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  deploy    Build and deploy the application"
    echo "  start     Start existing containers"
    echo "  stop      Stop running containers"
    echo "  restart   Restart the application"
    echo "  logs      Show application logs"
    echo "  status    Show container status"
    echo "  backup    Create database backup"
    echo "  restore   Restore from backup"
    echo "  clean     Remove containers and volumes"
    echo "  help      Show this help message"
}

# Function to start containers
start_containers() {
    print_status "Starting containers..."
    docker-compose -f "$COMPOSE_FILE" start
    print_success "Containers started!"
}

# Function to stop containers
stop_containers() {
    print_status "Stopping containers..."
    docker-compose -f "$COMPOSE_FILE" stop
    print_success "Containers stopped!"
}

# Function to restart application
restart_application() {
    print_status "Restarting application..."
    docker-compose -f "$COMPOSE_FILE" restart
    print_success "Application restarted!"
}

# Function to show logs
show_logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Function to create backup
create_backup() {
    print_status "Creating database backup..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="$BACKUP_DIR/manual_backup_$timestamp.sqlite3"
    
    if docker-compose -f "$COMPOSE_FILE" exec -T web cp db.sqlite3 "/tmp/backup.sqlite3"; then
        docker cp "$(docker-compose -f "$COMPOSE_FILE" ps -q web)":/tmp/backup.sqlite3 "$backup_file"
        print_success "Backup created: $backup_file"
    else
        print_error "Failed to create backup"
    fi
}

# Function to restore from backup
restore_backup() {
    print_status "Available backups:"
    ls -la "$BACKUP_DIR"/*.sqlite3 2>/dev/null || {
        print_error "No backup files found in $BACKUP_DIR"
        exit 1
    }
    
    echo ""
    read -p "Enter backup filename to restore: " backup_file
    
    if [ -f "$BACKUP_DIR/$backup_file" ]; then
        print_status "Restoring from $backup_file..."
        docker-compose -f "$COMPOSE_FILE" stop web
        docker cp "$BACKUP_DIR/$backup_file" "$(docker-compose -f "$COMPOSE_FILE" ps -q web)":/app/db.sqlite3
        docker-compose -f "$COMPOSE_FILE" start web
        print_success "Database restored successfully!"
    else
        print_error "Backup file not found: $BACKUP_DIR/$backup_file"
    fi
}

# Function to clean up
clean_deployment() {
    print_warning "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        print_status "Cleaning up deployment..."
        docker-compose -f "$COMPOSE_FILE" down -v --rmi all
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        check_prerequisites
        setup_environment
        deploy
        check_status
        ;;
    start)
        start_containers
        ;;
    stop)
        stop_containers
        ;;
    restart)
        restart_application
        ;;
    logs)
        show_logs
        ;;
    status)
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
    backup)
        create_backup
        ;;
    restore)
        restore_backup
        ;;
    clean)
        clean_deployment
        ;;
    help)
        show_usage
        ;;
    *)
        print_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac