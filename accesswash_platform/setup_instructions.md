# AccessWash Platform - Complete Setup Guide

## Prerequisites

Before starting, ensure you have:
- Python 3.8+ installed
- PostgreSQL with PostGIS extension
- Redis server (optional, for caching)
- Git

## Step 1: Repository Setup

```bash
# Clone the repository
git clone <your-accesswash-repo-url>
cd accesswash

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Step 2: Install Dependencies

```bash
# Install all required packages
pip install django djangorestframework django-tenants django-cors-headers
pip install drf-spectacular python-dotenv psycopg2-binary pillow
pip install django-filter celery redis
```

## Step 3: Database Setup

```bash
# Make the setup script executable
chmod +x setup_database.sh

# Run database setup
./setup_database.sh
```

This will create:
- Database: `accesswash_db`
- User: `accesswash_user`
- Password: `AccessWash2024!`
- PostGIS extensions enabled

## Step 4: Django Configuration

```bash
# Copy environment configuration
cp .env.example .env

# Edit .env file if needed (database credentials are already set)
nano .env
```

## Step 5: Copy Apps from Distro Repository

```bash
# Copy tenants app
cp -r ../distro/distro_backend/tenants/* ./tenants/

# Copy users app
cp -r ../distro/distro_backend/users/* ./users/

# Copy infrastructure as distro
cp -r ../distro/distro_backend/infrastructure/* ./distro/

# Update distro app name
sed -i "s/name = 'infrastructure'/name = 'distro'/g" distro/apps.py
sed -i "s/InfrastructureConfig/DistroConfig/g" distro/apps.py
```

## Step 6: Update All Import References

```bash
# Update imports in distro app
find ./distro -name "*.py" -exec sed -i 's/from infrastructure\./from distro\./g' {} +
find ./distro -name "*.py" -exec sed -i "s/'infrastructure'/'distro'/g" {} +
```

## Step 7: Run Migrations

```bash
# Create migrations
python manage.py makemigrations

# Run shared migrations
python manage.py migrate_schemas --shared

# Verify migration success
python manage.py showmigrations
```

## Step 8: Create Demo Data

```bash
# Run the comprehensive demo data setup
python setup_accesswash_data.py
```

## Step 9: Add Domain to Hosts File

```bash
# Add demo domain to your hosts file
echo "127.0.0.1 demo.accesswash.org" | sudo tee -a /etc/hosts
```

## Step 10: Start Development Server

```bash
# Start the Django development server
python manage.py runserver

# Server will be available at:
# - Platform: http://localhost:8000
# - Demo Utility: http://demo.accesswash.org:8000
```

## Access Points & Credentials

### Platform Administration
- **URL**: http://localhost:8000/admin/
- **Email**: admin@accesswash.org
- **Password**: AccessWash2024!

### Demo Utility Access
- **URL**: http://demo.accesswash.org:8000/admin/
- **Manager**: manager@nairobidemo.accesswash.org / Demo2024!
- **Supervisor**: supervisor@nairobidemo.accesswash.org / Demo2024!
- **Field Tech**: field1@nairobidemo.accesswash.org / Demo2024!
- **Customer Support**: support@nairobidemo.accesswash.org / Demo2024!

### API Documentation
- **Platform API**: http://localhost:8000/api/docs/
- **Demo Utility API**: http://demo.accesswash.org:8000/api/docs/

## Demo Data Overview

The setup creates:

### Infrastructure (Distro App)
- **5 Zones**: Westlands, Karen, Industrial Area, Kilimani, Kibera
- **30+ Assets**: Pipes, valves, meters, pump stations, reservoirs
- **40+ Inspections**: Asset inspection history
- **8 Asset Types**: Different infrastructure categories

### Customers
- **30 Customer Accounts**: 20 residential, 10 commercial
- **180+ Bills**: 6 months of billing history
- **45+ Service Requests**: Various types (repairs, billing, quality issues)

### Users & Access
- **5 Staff Users**: Different roles and permissions
- **Role-based access**: Admin, supervisor, field tech, customer service

## Testing the Setup

### Test API Endpoints
```bash
# Test infrastructure assets
curl http://demo.accesswash.org:8000/api/distro/assets/

# Test customer data
curl http://demo.accesswash.org:8000/api/customers/

# Test zones
curl http://demo.accesswash.org:8000/api/distro/zones/

# Test platform tenants
curl http://localhost:8000/api/tenants/
```

### Test Authentication
```bash
# Login to get JWT token
curl -X POST http://demo.accesswash.org:8000/api/users/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "manager@nairobidemo.accesswash.org", "password": "Demo2024!"}'
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Restart PostgreSQL if needed
sudo systemctl restart postgresql

# Test database connection
psql -h localhost -U accesswash_user -d accesswash_db
```

### Migration Issues
```bash
# Reset migrations if needed
python manage.py migrate_schemas --shared --fake-initial
python manage.py migrate_schemas --schema=demo --fake-initial
```

### Import Errors
```bash
# If you get import errors, check that all apps are created:
ls -la  # Should show: tenants, users, core, customers, distro, notifications

# Verify settings.py has all apps listed in SHARED_APPS and TENANT_APPS
```

## Next Steps

1. **Explore Admin Interfaces**: Login with different user roles
2. **Test API Endpoints**: Use the interactive API documentation
3. **Customize Demo Data**: Modify the setup script for your needs
4. **Add More Verticals**: Create huduma, maji, hesabu apps
5. **Frontend Development**: Start building React/Next.js frontend

## Development Workflow

```bash
# Daily development routine
source venv/bin/activate  # Activate virtual environment
python manage.py runserver  # Start development server

# Making model changes
python manage.py makemigrations
python manage.py migrate_schemas --shared
python manage.py migrate_schemas --schema=demo

# Adding new tenants
python manage.py shell
# Use Django shell to create new Utility and Domain objects
```

## Production Deployment Notes

For production deployment:
1. Change `DEBUG = False` in settings
2. Set proper `SECRET_KEY`
3. Configure production database
4. Set up proper domain DNS
5. Configure SSL certificates
6. Set up Redis for caching
7. Configure email settings for notifications

---

🎉 **AccessWash Platform is now ready for development!**