# 🌊 AccessWash Platform v1.00

**Digital Twin Platform for Water Utilities with Integrated Field Operations Management**

> **Target Market**: Water utilities in Kenya and Sub-Saharan Africa  
> **Launch Date**: Q2 2025  
> **Current Version**: 1.00 (Field Operations Ready)

---

## 🎯 Overview

AccessWash is a comprehensive **multi-tenant SaaS platform** designed specifically for water utilities to manage their infrastructure, field operations, and staff through an intuitive web interface with GIS capabilities.

### ✅ **Current Implementation (v1.00)**
```
accesswash-platform/
├── ✅ tenants/          → Platform management (multi-tenant setup)
├── ✅ users/            → Staff management (roles, auth, permissions)  
├── ✅ core/             → Utility settings & branding
└── ✅ distro/           → Field operations (infrastructure management)
```

### 🚧 **Planned Features (v2.0+)**
```
├── 🔮 customers/        → Customer management (AccessWASH Customer Portal)
├── 🔮 huduma/           → Customer support vertical
├── 🔮 maji/             → Water quality vertical
├── 🔮 hesabu/           → Billing vertical
└── 🔮 analytics/        → Reporting vertical
```

---

## 🚀 Key Features (v1.00)

### 🏢 **Multi-Tenant Architecture**
- **Isolated data environments** for each water utility
- **Custom domain routing** (api.accesswash.org, demo.accesswash.org)
- **Tenant-specific branding** and configuration
- **Scalable deployment** model

### 🗺️ **Interactive Infrastructure Mapping**
- **GIS-powered visualization** of water assets (pipes, valves, meters, pump stations)
- **Real-time asset tracking** with geolocation capabilities
- **PostGIS spatial data** support with SRID 4326 (WGS84)
- **Point-and-click asset addition** for field teams

### 👥 **Role-Based Access Control**
- **Admin Dashboard** with utility management
- **Supervisor Interface** for team oversight
- **Field Technician Tools** for asset management
- **Customer Service Portal** (future implementation)

### 🔧 **Maintenance Management**
- **Asset lifecycle tracking** (operational, maintenance, damaged)
- **Inspection workflows** with condition ratings
- **Photo documentation** for all maintenance activities
- **Equipment specifications** and metadata storage

### 🌐 **RESTful API**
- **Complete REST API** with JWT authentication
- **GeoJSON support** for spatial data
- **Interactive API documentation** (Swagger/ReDoc)
- **Spatial queries** (nearby assets, zone containment)

---

## 🛠️ Technology Stack

### **Backend**
- **Framework**: Django 5.1+ with django-tenants
- **Database**: PostgreSQL with PostGIS extensions
- **API**: Django REST Framework with JWT authentication
- **Spatial**: GeoDjango for GIS operations
- **Caching**: Redis (optional)

### **Key Dependencies**
- `django-tenants` - Multi-tenancy support
- `djangorestframework` - API framework
- `djangorestframework-gis` - Spatial API support
- `psycopg2-binary` - PostgreSQL adapter
- `drf-spectacular` - API documentation

### **Infrastructure**
- **Deployment**: Docker-ready
- **Database**: PostgreSQL 12+ with PostGIS 3+
- **Web Server**: Django development server (production: Gunicorn + Nginx)
- **Monitoring**: Django logging with file/console handlers

---

## ⚡ Quick Start (5 minutes)

### Prerequisites
- Python 3.8+
- PostgreSQL with PostGIS
- Git

### Installation
```bash
# 1. Clone repository
git clone https://github.com/fluxeng/accesswash.git
cd accesswash-platform

# 2. Setup environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Setup database
chmod +x setup_database.sh
./setup_database.sh

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Run migrations and create demo data
python manage.py migrate_schemas --shared
python setup_data.py

# 6. Add domains to hosts file to test on local development
echo "127.0.0.1 api.accesswash.org" | sudo tee -a /etc/hosts
echo "127.0.0.1 demo.accesswash.org" | sudo tee -a /etc/hosts

# 7. Start development server
python manage.py runserver
```

### Access Points The Rest to be Fleshed Out
- **Platform Management**: http://api.accesswash.org:8000/admin/
- **Demo Utility**: http://demo.accesswash.org:8000/admin/
- **API Documentation**: http://demo.accesswash.org:8000/api/docs/

---

## 📊 Current Capabilities (v1.00)

### **What AccessWASH Can Do Right Now:**

✅ **Multi-Utility Management**
- Create and manage multiple water utilities
- Isolated data per utility with proper tenant separation
- Custom branding and configuration per utility

✅ **Infrastructure Asset Management** 
- Track pipes, valves, meters, pump stations, reservoirs
- Spatial data with coordinates and zone boundaries
- Asset specifications and technical details
- Photo documentation and visual records

✅ **Field Operations**
- Asset inspections with condition ratings
- Maintenance scheduling and tracking
- Field team management with role-based access
- Mobile-friendly admin interface

✅ **User & Access Management**
- Role-based permissions (Admin, Supervisor, Field Tech, Customer Service)
- JWT authentication with secure login/logout
- User invitation system
- Activity tracking and audit trails

✅ **Spatial Data & GIS**
- PostGIS integration for spatial queries
- Support for points, lines, and polygons
- WKT, EWKT, and HEXEWKB format support
- Distance calculations and zone containment

✅ **API & Integration**
- RESTful API for all functionality
- GeoJSON support for mapping applications
- Comprehensive API documentation
- Token-based authentication

---

## 🏗️ Architecture

### **Multi-Tenant Design**
```
┌─────────────────────┐
│   Public Schema     │  ← Platform management
│  (api.accesswash)   │  ← Tenant administration
└─────────────────────┘
           │
           ├── Tenant: Nairobi Water (demo.accesswash.org)
           ├── Tenant: Mombasa Water (mombasa.accesswash.org)
           └── Tenant: Kisumu Water (kisumu.accesswash.org)
```

### **App Architecture**
- **tenants/**: Platform-level tenant management (public schema only)
- **users/**: User authentication and roles (both schemas)
- **core/**: Utility-specific settings and branding (tenant schemas only)
- **distro/**: Infrastructure and field operations (tenant schemas only)

### **Database Schema Separation**
- Each tenant gets its own PostgreSQL schema
- Complete data isolation between utilities
- Shared authentication and platform management
- Tenant-aware URL routing and admin interfaces

---

## 📖 Documentation To be Updated

### **For Internal Developers**
- [**Team Contributor Guide**](CONTRIBUTING.md) - Setup guide for new team members
- [**API Documentation**](http://demo.accesswash.org:8000/api/docs/) - Interactive API docs
- [**Spatial Data Guide**](docs/spatial-data.md) - Working with GIS data

### **For Users**
- [**Admin User Guide**](docs/admin-guide.md) - Platform administration
- [**Field Operations Manual**](docs/field-ops.md) - Asset management workflows
- [**Multi-Tenant Setup**](docs/tenant-setup.md) - Creating new utilities

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Test specific app
python manage.py test distro

# Test with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report

# Test API endpoints
curl http://demo.accesswash.org:8000/api/distro/assets/
```

---

## 🚀 Deployment

### **Development**
```bash
python manage.py runserver
```

### **Production** (Docker)
```bash
# Build and run with Docker
docker-compose up -d

# Or manual deployment
pip install gunicorn
gunicorn accesswash_platform.wsgi:application
```

### **Environment Variables**
```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
DB_NAME=accesswash_db
DB_USER=accesswash_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
```

---

## 🤝 Contributing

We welcome contributions! Please see our [**Contributing Guide**](CONTRIBUTING.md) for details.

### **Quick Start for Contributors**
```bash
# 1. Fork the repository
# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and test
python manage.py test

# 4. Commit and push
git commit -m "feat: add water quality monitoring"
git push origin feature/your-feature-name

# 5. Create pull request
```

### **Code Standards**
- Follow PEP 8 for Python code
- Use type hints where beneficial
- Write tests for new features
- Update documentation as needed
- Use conventional commit messages

---

## 📈 Roadmap

### **v1.1 (July 2025)**
- [ ] Enhanced mobile interface
- [ ] Bulk asset import/export
- [ ] Advanced spatial queries
- [ ] Performance optimizations

### **v2.0 (July 2025)**
- [ ] Customer management module
- [ ] Customer support ticketing (huduma)
- [ ] Water quality monitoring (maji)
- [ ] Basic billing system (hesabu)

### **v3.0 (August 2025)**
- [ ] Advanced analytics dashboard
- [ ] IoT sensor integration
- [ ] Mobile app for field workers
- [ ] Customer portal

---

## 📄 License

Proprietary software. All rights reserved.

---