#!/bin/bash

# Exit on error
set -e

echo "Starting Alice Is Missing Django Application..."

# Function to handle errors
handle_error() {
    echo "Error: $1"
    exit 1
}

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || handle_error "Failed to collect static files"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate || handle_error "Failed to apply migrations"

# Start Nginx
echo "Starting Nginx..."
sudo service nginx start || handle_error "Failed to start Nginx"

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn aliceismissing.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
