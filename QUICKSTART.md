# Company Leave Management System - Docker Quick Start

## 🚀 One-Command Deployment

### Prerequisites Check
```bash
# Verify Docker installation
docker --version
docker-compose --version
```

### Deploy in 30 Seconds
```bash
# Clone (if needed) and navigate to directory
cd company-leave-system

# Make scripts executable
chmod +x docker-deploy.sh docker-entrypoint.sh

# Deploy everything
make deploy
```

### Access Your Application
- **🌐 Web Interface**: http://localhost:8082
- **🛠️ Admin Panel**: http://localhost:8082/admin/
- **👤 Login**: admin / admin123

## 📋 Essential Commands

| Command | Description |
|---------|-------------|
| `make deploy` | Full deployment with setup |
| `make start` | Start containers |
| `make stop` | Stop containers |
| `make logs` | View application logs |
| `make status` | Check container status |
| `make backup` | Create database backup |
| `make shell` | Access Django shell |

## 🔧 Configuration

### Quick Environment Setup
```bash
# Copy template and edit
cp .env.docker .env
nano .env

# Key settings to change:
# DJANGO_SECRET_KEY=your-secret-key
# EMAIL_HOST=your-smtp-server
# COMPANY_NAME=Your Company
```

### Dataset Files Included
- ✅ Employee data (staff_list.csv)
- ✅ Sample data (sample_employees.csv) 
- ✅ System backup (company_leave_system_data.json)
- ✅ Automatic data loading on startup

## 🏭 Production Deployment

### Enable Production Mode
```bash
# Use production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or with Makefile
make prod-deploy
```

### SSL Certificate Setup
```bash
# Configure domain
export DOMAIN_NAME=your-domain.com
export SSL_EMAIL=admin@your-domain.com

# Deploy with SSL
docker-compose --profile ssl up -d
```

## 🔍 Troubleshooting

### Common Issues
```bash
# Permission errors
make data-permissions

# Port conflicts
netstat -tlnp | grep 8082

# Container logs
make logs-web

# Health check
make health
```

### Reset Everything
```bash
# Complete reset
make clean
make deploy
```

## 📊 Data Management

### Backup & Restore
```bash
# Create backup
make backup

# Restore from backup
make restore

# Load initial data
make loaddata
```

### Database Operations
```bash
# Run migrations
make migrate

# Create superuser
make createsuperuser

# Access database shell
make shell
```

## 🚦 Status Check

Run this to verify everything is working:
```bash
make info
make status
make health
```

Expected output:
```
✓ Containers running
✓ Application healthy  
✓ Database accessible
✓ Admin panel available
```

## 📞 Need Help?

1. **Check logs**: `make logs`
2. **Verify setup**: `make info`
3. **Reset if needed**: `make reset`
4. **Read full guide**: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

---

**🎯 Success Criteria**: If you can access http://localhost:8082/admin/ and login with admin/admin123, your deployment is successful!