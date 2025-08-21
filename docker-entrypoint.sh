#!/bin/bash

# Company Leave Management System - Docker Entrypoint Script
# Handles initialization and startup tasks for containerized deployment

set -e

echo "🏢 Starting Company Leave Management System..."

# Function to wait for database to be ready
wait_for_db() {
    echo "⏳ Waiting for database to be ready..."
    while ! python manage.py migrate --check >/dev/null 2>&1; do
        echo "⏳ Database not ready yet, waiting..."
        sleep 2
    done
    echo "✅ Database is ready!"
}

# Function to run database migrations
run_migrations() {
    echo "🗄️ Running database migrations..."
    python manage.py migrate --noinput
}

# Function to collect static files
collect_static() {
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput --clear
}

# Function to create superuser if it doesn't exist
create_superuser() {
    echo "👤 Checking for superuser..."
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@company.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️ Superuser already exists')
EOF
}

# Function to load initial data
load_initial_data() {
    if [ -f "staff_list.csv" ] && [ -f "load_csv_data.py" ]; then
        echo "📊 Loading initial employee data..."
        python load_csv_data.py || echo "⚠️ Could not load CSV data"
    fi
    
    if [ -f "company_leave_system_data.json" ]; then
        echo "📊 Loading system data..."
        python manage.py loaddata company_leave_system_data.json || echo "⚠️ Could not load JSON data"
    fi
}

# Function to set proper permissions
set_permissions() {
    echo "🔒 Setting proper permissions..."
    
    # Ensure database file is writable
    if [ -f "db.sqlite3" ]; then
        chmod 664 db.sqlite3
    fi
    
    # Ensure media directory exists and is writable
    mkdir -p media logs
    chmod 755 media logs
}

# Function to validate environment
validate_environment() {
    echo "🔍 Validating environment..."
    
    # Check if running in production mode
    if [ "$DJANGO_DEBUG" = "False" ]; then
        echo "🔒 Running in PRODUCTION mode"
        
        # Validate critical environment variables
        if [ "$DJANGO_SECRET_KEY" = "django-insecure-change-this-in-production" ]; then
            echo "⚠️ WARNING: Using default secret key in production!"
        fi
    else
        echo "🔧 Running in DEVELOPMENT mode"
    fi
}

# Main execution
main() {
    # Set permissions first
    set_permissions
    
    # Validate environment
    validate_environment
    
    # Wait for database
    wait_for_db
    
    # Run migrations
    run_migrations
    
    # Collect static files
    collect_static
    
    # Create superuser
    create_superuser
    
    # Load initial data
    load_initial_data
    
    echo "🚀 Starting Django development server..."
    echo "📱 Application will be available at: http://0.0.0.0:8000"
    echo "🛠️ Admin panel: http://0.0.0.0:8000/admin/"
    echo "👤 Default admin credentials: admin/admin123"
    echo ""
    
    # Execute the main command
    exec "$@"
}

# Run main function
main "$@"