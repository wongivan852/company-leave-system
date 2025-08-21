# Company Leave Management System - Docker Deployment Guide

This guide provides comprehensive instructions for containerizing and deploying the Company Leave Management System using Docker, specifically optimized for Linux Mint server environments.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Deployment Options](#deployment-options)
6. [Data Management](#data-management)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

## 🎯 Overview

### Application Architecture
- **Framework**: Django 4.2.23
- **Database**: SQLite (development) / PostgreSQL (production option)
- **Web Server**: Django development server (Gunicorn for production)
- **Reverse Proxy**: Nginx (optional, for production)
- **Container Runtime**: Docker with Docker Compose

### Container Structure
- **Web Container**: Django application with entrypoint automation
- **Backup Container**: Automated database backup service
- **Nginx Container**: Reverse proxy (production only)

## 🔧 Prerequisites

### System Requirements
- **OS**: Linux Mint 20+, Ubuntu 20.04+, or compatible
- **RAM**: Minimum 1GB, Recommended 2GB+
- **Storage**: 5GB+ available space
- **Network**: Internet access for initial setup

### Required Software
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## 🚀 Quick Start

### 1. Clone and Prepare
```bash
cd /path/to/company-leave-system
chmod +x docker-deploy.sh docker-entrypoint.sh
```

### 2. Deploy with Default Settings
```bash
./docker-deploy.sh deploy
```

### 3. Access Application
- **Web Interface**: http://localhost:8082
- **Admin Panel**: http://localhost:8082/admin/
- **Default Credentials**: admin / admin123

## ⚙️ Configuration

### Environment Variables

Copy and customize the environment file:
```bash
cp .env.docker .env
nano .env
```

#### Core Settings
```bash
# Security
DJANGO_SECRET_KEY=your-super-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,your-domain.com

# Email Configuration
EMAIL_HOST=smtp.yourcompany.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@yourcompany.com
EMAIL_HOST_PASSWORD=your-secure-password

# Database (for PostgreSQL option)
DATABASE_URL=postgresql://user:password@postgres:5432/leave_system
```

#### Company Settings
```bash
COMPANY_NAME=Your Company Name
COMPANY_EMAIL=hr@yourcompany.com
MAX_CONSECUTIVE_DAYS=14
SPECIAL_LEAVE_CREDITS_PER_SESSION=0.5
```

### Dataset Configuration

The system includes several dataset files that are automatically mounted:

- **staff_list.csv**: Employee master data
- **sample_employees.csv**: Sample data for testing
- **company_leave_system_data.json**: System configuration backup

## 🏗️ Deployment Options

### Development Deployment
```bash
# Standard development setup
./docker-deploy.sh deploy

# View logs
./docker-deploy.sh logs

# Stop application
./docker-deploy.sh stop
```

### Production Deployment
```bash
# Enable production profile with Nginx
docker-compose --profile production up -d

# Or use the deployment script
COMPOSE_PROFILES=production ./docker-deploy.sh deploy
```

### Custom Port Configuration
```bash
# Change port in docker-compose.yml
ports:
  - "8080:8000"  # External:Internal

# Or use environment variable
PORT=8080 docker-compose up -d
```

## 💾 Data Management

### Data Persistence

All critical data is persisted using Docker volumes:

```yaml
volumes:
  - ./data/db:/app/db.sqlite3          # Database
  - ./data/media:/app/media            # Uploaded files
  - ./data/logs:/app/logs              # Application logs
```

### Database Backup

#### Automatic Backups
- Runs every 24 hours automatically
- Keeps 7 days of backups
- Stored in `./backups/` directory

#### Manual Backup
```bash
./docker-deploy.sh backup
```

#### Restore from Backup
```bash
./docker-deploy.sh restore
```

### Data Migration

#### From Existing Installation
```bash
# Copy existing database
cp /path/to/existing/db.sqlite3 ./data/db/

# Copy media files
cp -r /path/to/existing/media/* ./data/media/

# Restart containers
./docker-deploy.sh restart
```

## 🏭 Production Deployment

### Security Hardening

1. **Update Environment Variables**:
```bash
# Generate secure secret key
DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Enable security features
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

2. **SSL Certificate Setup**:
```bash
# Create SSL directory
mkdir -p nginx/ssl

# Copy your certificates
cp your-cert.pem nginx/ssl/cert.pem
cp your-key.pem nginx/ssl/key.pem

# Update nginx configuration for HTTPS
```

3. **Firewall Configuration**:
```bash
# Ubuntu/Linux Mint firewall setup
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Performance Optimization

1. **Resource Limits**:
```yaml
# Add to docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

2. **Database Optimization**:
```bash
# For PostgreSQL production database
services:
  postgres:
    image: postgres:13-alpine
    environment:
      POSTGRES_DB: leave_system
      POSTGRES_USER: leave_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Health Monitoring

```bash
# Check application health
curl -f http://localhost:8082/admin/login/

# Monitor container status
docker-compose ps

# View resource usage
docker stats
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Permission Denied Errors
```bash
# Fix file permissions
sudo chown -R $USER:$USER ./data
chmod -R 755 ./data
```

#### 2. Database Lock Issues
```bash
# Stop all containers
docker-compose down

# Remove database lock
rm -f ./data/db/db.sqlite3-journal

# Restart containers
docker-compose up -d
```

#### 3. Port Already in Use
```bash
# Find process using port
sudo lsof -i :8082

# Change port in docker-compose.yml
ports:
  - "8083:8000"
```

#### 4. Container Build Failures
```bash
# Clean build cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

### Logging and Debugging

```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f web

# Enter container for debugging
docker-compose exec web bash

# Check Django configuration
docker-compose exec web python manage.py check
```

## 🔧 Maintenance

### Regular Maintenance Tasks

#### Weekly
```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean unused resources
docker system prune
```

#### Monthly
```bash
# Backup verification
./docker-deploy.sh backup

# Security updates
docker-compose down
docker-compose pull
docker-compose up -d
```

### Updates and Upgrades

#### Application Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and deploy
./docker-deploy.sh deploy
```

#### Database Migrations
```bash
# Run migrations manually
docker-compose exec web python manage.py migrate

# Check migration status
docker-compose exec web python manage.py showmigrations
```

### Scaling Considerations

For high-traffic deployments:

```yaml
# docker-compose.yml
services:
  web:
    deploy:
      replicas: 3
  
  nginx:
    depends_on:
      - web
    # Configure load balancing
```

## 📊 Monitoring and Metrics

### Application Metrics
- Monitor `/admin/login/` endpoint for health checks
- Track response times and error rates
- Monitor database query performance

### System Metrics
```bash
# Container resource usage
docker stats

# Disk usage
df -h ./data

# Log file sizes
du -sh ./data/logs/*
```

## 🆘 Support

### Getting Help
1. Check application logs: `./docker-deploy.sh logs`
2. Verify configuration: Review `.env` file
3. Test connectivity: `curl http://localhost:8082/admin/login/`
4. Check system resources: `docker stats`

### Emergency Recovery
```bash
# Complete system restore
./docker-deploy.sh clean
./docker-deploy.sh deploy
./docker-deploy.sh restore
```

This containerized deployment provides a robust, scalable solution for the Company Leave Management System, optimized for Linux Mint server environments with comprehensive data persistence, backup strategies, and production-ready features.