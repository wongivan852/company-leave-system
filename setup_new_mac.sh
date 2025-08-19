#!/bin/bash

# Company Leave System - Quick Setup Script for New Mac
# Run this script to automatically set up the leave management system

set -e  # Exit on any error

echo "🏢 Company Leave System - Quick Setup"
echo "====================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first:"
    echo "   brew install python3"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Please run this script from the company-leave-system directory"
    echo "   cd /path/to/company-leave-system"
    exit 1
fi

echo "✅ Found Django project files"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Setting up database..."
python manage.py migrate

# Check if superuser exists, if not prompt to create one
echo "👤 Checking for admin user..."
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
django.setup()
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No admin user found. Please create one:')
    exit(1)
else:
    print('Admin user already exists.')
" || {
    echo "Creating admin user..."
    python manage.py createsuperuser
}

# Load sample data
echo "📊 Loading sample data..."
python manage.py import_employees sample_employees.csv || echo "⚠️  Sample employees not imported (file may not exist)"

# Run system check
echo "🔍 Running system check..."
python manage.py check

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "To start the application:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start server: python manage.py runserver"
echo "3. Open browser: http://127.0.0.1:8000"
echo ""
echo "Admin panel: http://127.0.0.1:8000/admin/"
echo ""
echo "📚 See SETUP_NEW_MAC.md for detailed instructions"
