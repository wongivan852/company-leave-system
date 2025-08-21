# Company Leave Management System - Multi-stage Docker Build
# Optimized for production deployment on Linux Mint servers

# Stage 1: Base Python environment
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base as dependencies

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Application
FROM dependencies as application

# Create non-root user for security
RUN groupadd -r django && useradd -r -g django django

# Set working directory
WORKDIR /app

# Copy entrypoint script first
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Copy application code
COPY --chown=django:django . .

# Copy dataset files explicitly
COPY --chown=django:django *.csv ./
COPY --chown=django:django *.json ./

# Create necessary directories
RUN mkdir -p /app/media /app/static /app/logs && \
    chown -R django:django /app

# Copy environment template if .env doesn't exist
RUN if [ ! -f .env ]; then cp env.example .env; fi && \
    chown django:django .env

# Set proper permissions for database and manage.py
RUN chmod +x manage.py && \
    chmod 664 db.sqlite3 2>/dev/null || echo "db.sqlite3 not found, will be created" && \
    chown django:django db.sqlite3 2>/dev/null || echo "db.sqlite3 ownership will be set on creation"

# Switch to non-root user
USER django

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]