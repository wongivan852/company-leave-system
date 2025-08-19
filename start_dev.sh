#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start the Django development server
echo "Starting Company Leave System on http://127.0.0.1:8083"
echo "Admin login: admin (password will be prompted on first login)"
echo "Press Ctrl+C to stop the server"
echo ""

python manage.py runserver 0.0.0.0:8083
