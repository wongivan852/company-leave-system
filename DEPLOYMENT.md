# Deployment Guide

This guide provides step-by-step instructions for deploying the Company Leave Management System to various platforms.

## 🚀 Quick Deployment Options

### Option 1: Heroku (Recommended for beginners)
### Option 2: DigitalOcean App Platform  
### Option 3: AWS EC2 with RDS
### Option 4: VPS with Docker

---

## 🔧 Pre-Deployment Checklist

### 1. Environment Configuration
- [ ] Set `DEBUG=False` in production settings
- [ ] Configure secure `SECRET_KEY`
- [ ] Set up production database (PostgreSQL recommended)
- [ ] Configure email settings for notifications
- [ ] Set `ALLOWED_HOSTS` for your domain
- [ ] Configure static file serving

### 2. Database Preparation
- [ ] Run all migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Load initial data if needed
- [ ] Test database connectivity

### 3. Security Setup
- [ ] Enable HTTPS/SSL
- [ ] Configure CSRF settings
- [ ] Set up secure headers
- [ ] Configure session security
- [ ] Set up firewall rules

---

## 🌐 Heroku Deployment

### Step 1: Prepare for Heroku
1. Install Heroku CLI
2. Create Heroku account
3. Install additional packages:
```bash
pip install gunicorn dj-database-url whitenoise psycopg2-binary
pip freeze > requirements.txt
```

### Step 2: Create Heroku Configuration Files

**Procfile:**
```
web: gunicorn leave_system.wsgi
release: python manage.py migrate
```

**runtime.txt:**
```
python-3.11.7
```

### Step 3: Update Django Settings
Create `leave_system/production_settings.py`:
```python
from .settings import *
import dj_database_url
import os

DEBUG = False
ALLOWED_HOSTS = ['your-app-name.herokuapp.com', 'yourdomain.com']

# Database
DATABASES = {
    'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
}

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### Step 4: Deploy to Heroku
```bash
# Login to Heroku
heroku login

# Create Heroku app
heroku create your-app-name

# Set environment variables
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DJANGO_SETTINGS_MODULE="leave_system.production_settings"

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Create superuser
heroku run python manage.py createsuperuser
```

---

## 🐋 Docker Deployment

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "leave_system.wsgi:application"]
```

### Step 2: Create docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=your-secret-key
      - DATABASE_URL=postgresql://user:password@db:5432/leave_system
    depends_on:
      - db
    volumes:
      - ./static:/app/static

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=leave_system
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Step 3: Deploy with Docker
```bash
# Build and run
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

---

## ☁️ AWS EC2 Deployment

### Step 1: Launch EC2 Instance
1. Choose Ubuntu 22.04 LTS
2. Configure security groups (ports 22, 80, 443)
3. Create and download key pair

### Step 2: Server Setup
```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv nginx postgresql postgresql-contrib -y

# Create application user
sudo adduser django
sudo usermod -aG sudo django
```

### Step 3: Application Setup
```bash
# Switch to django user
sudo su - django

# Clone repository
git clone https://github.com/yourusername/company-leave-system.git
cd company-leave-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Set up environment
cp env.example .env
# Edit .env with production settings
```

### Step 4: Database Setup
```bash
# Configure PostgreSQL
sudo -u postgres createdb leave_system
sudo -u postgres createuser --interactive django

# Run migrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```

### Step 5: Configure Services

**Gunicorn service (`/etc/systemd/system/leave-system.service`):**
```ini
[Unit]
Description=Leave System Gunicorn daemon
After=network.target

[Service]
User=django
Group=www-data
WorkingDirectory=/home/django/company-leave-system
ExecStart=/home/django/company-leave-system/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/home/django/company-leave-system/leave_system.sock leave_system.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Nginx configuration (`/etc/nginx/sites-available/leave-system`):**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /home/django/company-leave-system;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/django/company-leave-system/leave_system.sock;
    }
}
```

### Step 6: Start Services
```bash
# Enable and start Gunicorn
sudo systemctl daemon-reload
sudo systemctl start leave-system
sudo systemctl enable leave-system

# Configure Nginx
sudo ln -s /etc/nginx/sites-available/leave-system /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

# Enable firewall
sudo ufw allow 'Nginx Full'
```

---

## 🔒 SSL Certificate Setup

### Using Certbot (Let's Encrypt)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## 📊 Production Monitoring

### 1. Application Monitoring
- Set up Django logging
- Configure error tracking (Sentry)
- Monitor performance metrics

### 2. Server Monitoring
- Set up system monitoring (htop, iostat)
- Configure log rotation
- Monitor disk space and memory

### 3. Database Monitoring
- Set up PostgreSQL monitoring
- Configure backup schedules
- Monitor query performance

---

## 🔧 Maintenance Tasks

### Regular Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Python packages
pip install -U -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart leave-system
```

### Backup Procedures
```bash
# Database backup
pg_dump leave_system > backup_$(date +%Y%m%d_%H%M%S).sql

# Application backup
tar -czf app_backup_$(date +%Y%m%d_%H%M%S).tar.gz /home/django/company-leave-system
```

---

## 🚨 Troubleshooting

### Common Issues

**Static files not loading:**
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Run `python manage.py collectstatic`
- Verify Nginx static file configuration

**Database connection errors:**
- Check database credentials in `.env`
- Verify PostgreSQL service is running
- Check firewall settings

**Permission errors:**
- Verify file ownership: `chown -R django:www-data /path/to/app`
- Check file permissions: `chmod 755` for directories, `644` for files

**Service won't start:**
- Check logs: `sudo journalctl -u leave-system -f`
- Verify virtual environment path in service file
- Test Gunicorn manually

### Getting Help
- Check application logs: `tail -f /var/log/nginx/error.log`
- Monitor system resources: `htop`, `df -h`, `free -h`
- Test configuration: `nginx -t`, `python manage.py check --deploy`

---

**Need help?** Create an issue in the GitHub repository with your deployment platform and error details.
