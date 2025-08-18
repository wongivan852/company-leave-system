#!/bin/bash

# Company Leave System - Simple Startup Script
# Run this to quickly start the development server

set -e

echo "🏢 Starting Company Leave System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup_new_mac.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please update .env with your settings"
fi

# Run migrations if needed
echo "🗄️  Checking database..."
python manage.py migrate --check >/dev/null 2>&1 || {
    echo "🔄 Running database migrations..."
    python manage.py migrate
}

# Start the development server
echo "🚀 Starting development server..."
echo "📱 Application will be available at: http://127.0.0.1:8083"
echo "🛠️  Admin panel: http://127.0.0.1:8083/admin/"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python manage.py runserver 0.0.0.0:8083