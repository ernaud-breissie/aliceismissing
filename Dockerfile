# Base stage for Python dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DJANGO_SETTINGS_MODULE=aliceismissing.settings

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=aliceismissing.settings \
    PATH="/opt/venv/bin:$PATH"

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv

# Install Nginx and required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    sudo \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash app && \
    echo "app ALL=(ALL) NOPASSWD: /usr/sbin/service nginx start" >> /etc/sudoers.d/app

# Create necessary directories
RUN mkdir -p /app/media /app/static /app/staticfiles && \
    chown -R app:app /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/media /app/static /app/staticfiles

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=app:app . .

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/sites-available/default

# Make scripts executable
RUN chmod +x entrypoint.sh

# Configure volumes for persistent data
VOLUME ["/app/media", "/app/static", "/app/db.sqlite3"]

# Switch to non-root user
USER app

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health/ || exit 1

# Start Nginx and Gunicorn
CMD ["./entrypoint.sh"]
