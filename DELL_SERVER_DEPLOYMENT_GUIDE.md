# Dell Server Deployment Guide - Company Leave System

## Overview

This comprehensive guide provides production-tested instructions for deploying the Company Leave System on Dell servers running Ubuntu 24.04 LTS. Based on real-world deployment experience from CRM systems and Stripe dashboards, this guide incorporates lessons learned from actual production deployments.

The Company Leave System is a Django-based application for managing employee leave requests, approvals, and holiday management with comprehensive workflow automation.

## Prerequisites

- Dell server with Ubuntu 24.04 LTS (required for compatibility)
- Root access to the server
- Network connectivity (intranet and internet)
- Minimum 8GB RAM, 50GB storage (recommended: 16GB RAM, 100GB storage)
- Git installed on the server

## Deployment Architecture

```
Internet/Intranet
       ↓
    Nginx (Port 80/443)
       ↓
  Company Leave System (Port 8083)
       ↓
  PostgreSQL Database
```

## Ubuntu 24.04 Compatibility Requirements

**Critical**: Ubuntu 24.04 uses externally managed Python environments. Always use system packages for Python dependencies:

```bash
# ✅ Correct for Ubuntu 24.04
sudo apt install python3-venv python3-pip python3-dev

# ❌ Incorrect - will fail on Ubuntu 24.04
pip3 install --system virtualenv
```

## Step 1: System Preparation

### 1.1 System Update
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Install Core Dependencies
```bash
# Python environment (Ubuntu 24.04 compatible)
sudo apt install -y python3 python3-venv python3-pip python3-dev

# Database and caching
sudo apt install -y postgresql postgresql-contrib redis-server

# Web server and security
sudo apt install -y nginx fail2ban ufw

# Development tools
sudo apt install -y git curl wget build-essential libpq-dev

# Monitoring tools
sudo apt install -y htop iotop netstat lsof
```

### 1.3 Security Setup
```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw allow 8083/tcp comment 'Company Leave System'
sudo ufw enable

# Configure fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Step 2: Database Setup

### 2.1 PostgreSQL Configuration
```bash
# Switch to postgres user
sudo -u postgres psql

# Create production database
CREATE DATABASE company_leave_system_db;
CREATE USER leave_system_user WITH PASSWORD 'secure_leave_password_2025';
GRANT ALL PRIVILEGES ON DATABASE company_leave_system_db TO leave_system_user;
ALTER USER leave_system_user CREATEDB;
\q

# Enable and start PostgreSQL
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 2.2 Redis Configuration
```bash
# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Configure Redis security
sudo nano /etc/redis/redis.conf
# Add: requirepass your_redis_password

sudo systemctl restart redis-server
```

## Step 3: Application Setup

### 3.1 Create Application User and Directory
```bash
# Create dedicated user for company leave system
sudo useradd -r -d /opt/company-leave-system -s /bin/bash leavesys
sudo mkdir -p /opt/company-leave-system
sudo chown -R leavesys:leavesys /opt/company-leave-system

# Create application directories
sudo mkdir -p /opt/company-leave-system/{app,logs,data,backups,media}
sudo mkdir -p /var/log/company-leave-system
sudo mkdir -p /var/lib/company-leave-system
```

### 3.2 Deploy Application Code
```bash
# Clone the company leave system
cd /tmp
git clone https://github.com/wongivan852/company-leave-system.git
sudo cp -r company-leave-system/* /opt/company-leave-system/app/

# Set proper ownership
sudo chown -R leavesys:leavesys /opt/company-leave-system
sudo chown -R leavesys:leavesys /var/log/company-leave-system
sudo chown -R leavesys:leavesys /var/lib/company-leave-system
```

### 3.3 Python Environment Setup
```bash
cd /opt/company-leave-system/app

# Create virtual environment (Ubuntu 24.04 compatible)
sudo -u leavesys python3 -m venv ../venv

# Activate environment and install dependencies
sudo -u leavesys bash -c "
source ../venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
"
```

## Step 4: Environment Configuration

### 4.1 Create Environment File
```bash
sudo -u leavesys nano /opt/company-leave-system/.env
```

### 4.2 Production Environment Variables
```bash
# Security Configuration
SECRET_KEY=your_generated_secret_key_here_64_chars_minimum
DEBUG=False
ENVIRONMENT=production

# Database Configuration (PostgreSQL - Production Ready)
DATABASE_URL=postgresql://leave_system_user:secure_leave_password_2025@localhost:5432/company_leave_system_db
CONN_MAX_AGE=600

# Redis Configuration
REDIS_URL=redis://:your_redis_password@localhost:6379/0

# Network Configuration
HOST=0.0.0.0
PORT=8083
ALLOWED_HOSTS=your-server-ip,your-domain.com,localhost,127.0.0.1,192.168.0.104
CSRF_TRUSTED_ORIGINS=https://your-server-ip,https://your-domain.com

# Company Configuration
COMPANY_NAME=Your Company Name
COMPANY_EMAIL=admin@yourcompany.com
COMPANY_PHONE=+852-1234-5678

# Leave System Specific Configuration
DEFAULT_ANNUAL_LEAVE_DAYS=18
DEFAULT_SICK_LEAVE_DAYS=120
REQUIRE_MANAGER_APPROVAL=True
ALLOW_HALF_DAY_LEAVE=True
BUSINESS_DAYS_NOTICE=3

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@company.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=leave-system@your-domain.com

# File Upload Configuration
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_FILE_EXTENSIONS=pdf,doc,docx,jpg,jpeg,png

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/company-leave-system/leave-system.log
ERROR_LOG_FILE=/var/log/company-leave-system/error.log

# Performance Configuration (Based on Dell Server Testing)
WORKER_PROCESSES=3
WORKER_TIMEOUT=120
MAX_REQUESTS=1000
KEEPALIVE=2

# Backup Configuration
BACKUP_RETENTION_DAYS=30
AUTO_BACKUP_ENABLED=True
```

### 4.3 Generate Secret Key
```bash
# Generate secure secret key
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" | sudo -u leavesys tee -a /opt/company-leave-system/.env
```

## Step 5: Django Application Setup

### 5.1 Configure Django Settings for Production
```bash
sudo -u leavesys nano /opt/company-leave-system/app/leave_system/settings.py
```

Add production database configuration:
```python
import os
from pathlib import Path
import dj_database_url

# Database configuration for production
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    # Fallback to SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = '/opt/company-leave-system/staticfiles'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = '/opt/company-leave-system/media'

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/company-leave-system/leave-system.log',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/company-leave-system/error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'leave': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 5.2 Database Migration and Setup
```bash
cd /opt/company-leave-system/app
sudo -u leavesys bash -c "
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
"
```

### 5.3 Create Superuser
```bash
sudo -u leavesys bash -c "
cd /opt/company-leave-system/app
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python manage.py createsuperuser
"
```

### 5.4 Import Initial Data (Optional)
```bash
# Import employees from CSV if available
sudo -u leavesys bash -c "
cd /opt/company-leave-system/app
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python manage.py import_employees --csv-file=staff_list.csv
python manage.py import_holidays --year=2025
"
```

## Step 6: Systemd Service Configuration

### 6.1 Create Systemd Service File
```bash
sudo nano /etc/systemd/system/company-leave-system.service
```

### 6.2 Service Configuration (Production Tested)
```ini
[Unit]
Description=Company Leave System Django Application
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service
Wants=network-online.target

[Service]
Type=simple
User=leavesys
Group=leavesys
WorkingDirectory=/opt/company-leave-system/app
Environment=PATH=/opt/company-leave-system/venv/bin
EnvironmentFile=/opt/company-leave-system/.env

# Production tested command with Gunicorn
ExecStart=/opt/company-leave-system/venv/bin/gunicorn \
    --workers 3 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --keepalive 2 \
    --bind 0.0.0.0:8083 \
    --user leavesys \
    --group leavesys \
    --access-logfile /var/log/company-leave-system/access.log \
    --error-logfile /var/log/company-leave-system/error.log \
    --log-level info \
    leave_system.wsgi:application

ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStartSec=120
TimeoutStopSec=30
RestartSec=10
Restart=always

# Security settings
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/company-leave-system /var/log/company-leave-system /var/lib/company-leave-system
NoNewPrivileges=true

# Resource limits
MemoryLimit=2G
CPUQuota=200%

# Watchdog settings (Critical: Based on Production Experience)
WatchdogSec=120
NotifyAccess=all

[Install]
WantedBy=multi-user.target
```

### 6.3 Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable company-leave-system
sudo systemctl start company-leave-system

# Check status
sudo systemctl status company-leave-system
```

## Step 7: Nginx Reverse Proxy Setup

### 7.1 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/company-leave-system
```

### 7.2 Nginx Configuration (Production Optimized)
```nginx
# Rate limiting configuration
limit_req_zone $binary_remote_addr zone=leave_system:10m rate=10r/m;
limit_req_status 429;

# Upstream configuration
upstream leave_system_backend {
    server 127.0.0.1:8083 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com your-server-ip 192.168.0.104;
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline'" always;
    
    # Hide server version
    server_tokens off;
    
    # Client settings
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    
    # Logging
    access_log /var/log/nginx/leave-system-access.log;
    error_log /var/log/nginx/leave-system-error.log warn;
    
    # Main application proxy
    location / {
        # Rate limiting
        limit_req zone=leave_system burst=20 nodelay;
        
        # Proxy configuration
        proxy_pass http://leave_system_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts (Based on Production Experience)
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # Keep-alive
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Static files
    location /static/ {
        alias /opt/company-leave-system/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Security for static files
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Media files (uploaded files)
    location /media/ {
        alias /opt/company-leave-system/media/;
        expires 1M;
        add_header Cache-Control "public";
        
        # Security for uploaded files
        location ~* \.(pdf|doc|docx)$ {
            add_header Content-Disposition "attachment";
        }
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://leave_system_backend/health;
        access_log off;
    }
    
    # Block common attack patterns
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~* \.(sql|bak|backup|old)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # Block access to sensitive Django files
    location ~* /(settings|local_settings)\.py$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

### 7.3 Enable Nginx Configuration
```bash
# Test configuration
sudo nginx -t

# Enable site
sudo ln -s /etc/nginx/sites-available/company-leave-system /etc/nginx/sites-enabled/

# Remove default site if needed
sudo rm -f /etc/nginx/sites-enabled/default

# Restart services
sudo systemctl restart nginx
sudo systemctl restart company-leave-system
```

## Step 8: SSL/HTTPS Configuration

### 8.1 Self-Signed Certificate (Internal Network)
```bash
# Create SSL directory
sudo mkdir -p /etc/ssl/company-leave-system

# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/company-leave-system/leave-system.key \
  -out /etc/ssl/company-leave-system/leave-system.crt \
  -subj "/C=HK/ST=Hong Kong/L=Hong Kong/O=Your Organization/CN=192.168.0.104"

# Set proper permissions
sudo chmod 600 /etc/ssl/company-leave-system/leave-system.key
sudo chmod 644 /etc/ssl/company-leave-system/leave-system.crt
```

### 8.2 Update Nginx for HTTPS
```bash
sudo nano /etc/nginx/sites-available/company-leave-system
```

Add HTTPS server block:
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com your-server-ip 192.168.0.104;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/company-leave-system/leave-system.crt;
    ssl_certificate_key /etc/ssl/company-leave-system/leave-system.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # [Copy the rest of the location blocks from the HTTP configuration]
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com your-server-ip 192.168.0.104;
    return 301 https://$server_name$request_uri;
}
```

## Step 9: Health Check and Monitoring

### 9.1 Create Health Check Endpoint
Create a simple health check view in Django:

```python
# Add to leave/views.py or create a new file
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection

@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint"""
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'company-leave-system',
            'port': 8083,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)
```

Add to URLs:
```python
# In leave_system/urls.py
from django.urls import path, include
from leave.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('', include('leave.urls')),
]
```

### 9.2 Health Check Script
```bash
sudo nano /usr/local/bin/leave-system-health-check
```

```bash
#!/bin/bash
echo "=== Company Leave System Health Check ==="
echo "Date: $(date)"
echo ""

# Service status
echo "Service Status:"
systemctl is-active company-leave-system
systemctl is-active postgresql
systemctl is-active redis-server
systemctl is-active nginx

# Port status
echo ""
echo "Port Status:"
netstat -tulpn | grep -E ":8083|:80|:443"

# Database connection
echo ""
echo "Database Connection:"
sudo -u leavesys psql -d company_leave_system_db -c "SELECT 1;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "PostgreSQL: OK"
else
    echo "PostgreSQL: FAILED"
fi

# Redis connection
echo ""
echo "Redis Connection:"
redis-cli -a your_redis_password ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Redis: OK"
else
    echo "Redis: FAILED"
fi

# Application response
echo ""
echo "Application Response:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8083/health 2>/dev/null | grep -q "200"
if [ $? -eq 0 ]; then
    echo "Leave System: OK"
else
    echo "Leave System: FAILED"
fi

# Resource usage
echo ""
echo "Resource Usage:"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
```

```bash
sudo chmod +x /usr/local/bin/leave-system-health-check
```

## Step 10: Backup Strategy

### 10.1 Backup Script
```bash
sudo nano /usr/local/bin/backup-company-leave-system
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/company-leave-system"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR/$DATE"

echo "Starting backup at $(date)"

# Database backup
echo "Backing up database..."
sudo -u leavesys pg_dump company_leave_system_db > "$BACKUP_DIR/$DATE/database.sql"

# Application files backup
echo "Backing up application files..."
tar -czf "$BACKUP_DIR/$DATE/application.tar.gz" /opt/company-leave-system --exclude=/opt/company-leave-system/venv

# Media files backup (uploaded documents)
echo "Backing up media files..."
tar -czf "$BACKUP_DIR/$DATE/media.tar.gz" /opt/company-leave-system/media

# Configuration backup
echo "Backing up configuration files..."
cp -r /etc/nginx/sites-available/company-leave-system "$BACKUP_DIR/$DATE/"
cp /etc/systemd/system/company-leave-system.service "$BACKUP_DIR/$DATE/"
cp /opt/company-leave-system/.env "$BACKUP_DIR/$DATE/"

# Employee data export (CSV format)
echo "Exporting current employee data..."
sudo -u leavesys bash -c "
cd /opt/company-leave-system/app
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python manage.py dumpdata leave.Employee --format=json > \"$BACKUP_DIR/$DATE/employees.json\"
python manage.py dumpdata leave.LeaveApplication --format=json > \"$BACKUP_DIR/$DATE/leave_applications.json\"
"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null

echo "Backup completed: $BACKUP_DIR/$DATE"
echo "Backup size: $(du -sh $BACKUP_DIR/$DATE | cut -f1)"
```

```bash
sudo chmod +x /usr/local/bin/backup-company-leave-system

# Schedule daily backups
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-company-leave-system
```

## Step 11: Dell Hardware Optimization

### 11.1 Network Optimization
```bash
# Check Dell network adapter
sudo lspci | grep -E "(Network|Ethernet)"
sudo ethtool eth0

# Optimize for Dell hardware
sudo ethtool -G eth0 rx 2048 tx 2048
sudo ethtool -K eth0 tso on gso on

# Make permanent
echo "ethtool -G eth0 rx 2048 tx 2048" | sudo tee -a /etc/rc.local
echo "ethtool -K eth0 tso on gso on" | sudo tee -a /etc/rc.local
```

### 11.2 Memory Optimization for Dell Servers
```bash
sudo nano /etc/sysctl.conf

# Add Dell-optimized settings
vm.swappiness=10
vm.vfs_cache_pressure=50
vm.dirty_ratio=15
vm.dirty_background_ratio=5
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216

# Apply settings
sudo sysctl -p
```

## Step 12: Testing and Validation

### 12.1 System Tests
```bash
# Test all services
sudo systemctl status company-leave-system postgresql redis-server nginx

# Test network connectivity
curl -k https://localhost/health
curl http://localhost:8083/health

# Test database connectivity
sudo -u leavesys psql -d company_leave_system_db -c "SELECT version();"

# Test Redis connectivity
redis-cli -a your_redis_password ping
```

### 12.2 Application Functionality Tests
```bash
# Test Django management commands
sudo -u leavesys bash -c "
cd /opt/company-leave-system/app
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python manage.py check
python manage.py test
"

# Test leave application workflow
# Access the web interface and test:
# 1. Employee registration and login
# 2. Leave application submission
# 3. Manager approval workflow
# 4. Leave balance calculation
# 5. Holiday management
# 6. Report generation
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Service Won't Start
```bash
# Check service status and logs
sudo systemctl status company-leave-system
sudo journalctl -u company-leave-system -f

# Check port availability
sudo netstat -tulpn | grep :8083

# Test Django application directly
sudo -u leavesys bash -c "
cd /opt/company-leave-system/app
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python manage.py runserver 0.0.0.0:8083
"
```

#### 2. Database Connection Issues
```bash
# Test database connection
sudo -u leavesys psql -d company_leave_system_db -c "SELECT 1;"

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Reset database if needed
sudo -u postgres dropdb company_leave_system_db
sudo -u postgres createdb company_leave_system_db
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE company_leave_system_db TO leave_system_user;"
```

#### 3. File Upload Issues
```bash
# Check media directory permissions
ls -la /opt/company-leave-system/media/
sudo chown -R leavesys:leavesys /opt/company-leave-system/media/
sudo chmod -R 755 /opt/company-leave-system/media/

# Check Nginx upload size
sudo nano /etc/nginx/sites-available/company-leave-system
# Ensure client_max_body_size is set appropriately
```

#### 4. Email Notification Issues
```bash
# Test email configuration
sudo -u leavesys bash -c "
cd /opt/company-leave-system/app
source ../venv/bin/activate
export $(grep -v '^#' ../.env | xargs)
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
"
```

## Quick Reference

### Essential Commands
```bash
# Service management
sudo systemctl {start|stop|restart|status} company-leave-system
sudo systemctl {start|stop|restart|status} nginx

# View logs
sudo journalctl -u company-leave-system -f
sudo tail -f /var/log/company-leave-system/error.log
sudo tail -f /var/log/nginx/leave-system-error.log

# Health checks
/usr/local/bin/leave-system-health-check
curl -k https://localhost/health

# Database management
sudo -u leavesys psql -d company_leave_system_db
sudo -u postgres pg_dump company_leave_system_db > backup.sql

# Django management
cd /opt/company-leave-system/app
sudo -u leavesys bash -c "source ../venv/bin/activate && python manage.py shell"

# Backup
/usr/local/bin/backup-company-leave-system
```

### File Locations
- **Application**: `/opt/company-leave-system/`
- **Virtual Environment**: `/opt/company-leave-system/venv/`
- **Configuration**: `/opt/company-leave-system/.env`
- **Logs**: `/var/log/company-leave-system/`
- **Database**: PostgreSQL `company_leave_system_db`
- **Media Files**: `/opt/company-leave-system/media/`
- **Backups**: `/var/backups/company-leave-system/`
- **SSL Certificates**: `/etc/ssl/company-leave-system/`

### Access URLs
- **HTTP**: `http://server-ip/`
- **HTTPS**: `https://server-ip/`
- **Health Check**: `https://server-ip/health`
- **Admin Panel**: `https://server-ip/admin/`
- **Direct Access**: `http://server-ip:8083/`

## Production Deployment Checklist

- [ ] Ubuntu 24.04 LTS installed and updated
- [ ] All required packages installed using apt (not pip)
- [ ] PostgreSQL database created and configured
- [ ] Redis server installed and secured
- [ ] Application user created with proper permissions
- [ ] Virtual environment created and dependencies installed
- [ ] Environment file configured with secure values
- [ ] Database migrations completed
- [ ] Static files collected
- [ ] Superuser account created
- [ ] Initial data imported (employees, holidays)
- [ ] Systemd service configured with 120s watchdog timeout
- [ ] Gunicorn installed and configured (3 workers, 120s timeout)
- [ ] Nginx reverse proxy configured with security headers
- [ ] SSL certificates generated and configured
- [ ] Firewall rules configured (UFW)
- [ ] Fail2ban configured for security
- [ ] Log rotation configured
- [ ] Health check script created and scheduled
- [ ] Backup script created and scheduled
- [ ] Dell hardware optimizations applied
- [ ] All services tested and operational
- [ ] Application functionality tested
- [ ] Documentation updated with server-specific details

This deployment guide ensures a secure, scalable, and maintainable installation of the Company Leave System on your Dell server with optimal performance and reliability, using port 8083 for the application service.