# 🤝 AccessWash Platform - Team Contributor Setup Guide

## 🎯 For New Team Members

This guide helps new developers join the AccessWash team and start contributing immediately.

---

## 🚀 Quick Start (15 minutes)

### Prerequisites Check
```bash
# Verify you have these installed:
python --version    # Should be 3.8+
psql --version      # PostgreSQL with PostGIS
git --version       # Git for version control
redis-cli ping      # Redis (optional)
```

### 1. Get the Code
```bash
# Clone the repository
git clone https://github.com/yourusername/accesswash-platform.git
cd accesswash-platform

# Create your feature branch
git checkout -b feature/your-name-setup

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR 
venv\Scripts\activate     # Windows
```

### 2. Install Dependencies
```bash
# Install all requirements
pip install -r requirements.txt

# Verify installation
python manage.py --version
```

### 3. Database Setup
```bash
# Run the database setup script
chmod +x setup_database.sh
./setup_database.sh

# This creates:
# - PostgreSQL database: accesswash_db
# - User: accesswash_user
# - Password: AccessWash2024!
# - PostGIS extensions enabled
```

### 4. Environment Configuration
```bash
# Create .env file (copy and paste this)
cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=django-insecure-accesswash-dev-change-in-production
DB_NAME=accesswash_db
DB_USER=accesswash_user
DB_PASSWORD=AccessWash2024!
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379/1
EOF
```

### 5. Setup Database & Demo Data
```bash
# Create migrations
python manage.py makemigrations

# Run migrations for shared schema
python manage.py migrate_schemas --shared

# Create demo tenant and sample data
python setup_data.py

# Add domains to hosts file
echo "127.0.0.1 api.accesswash.org" | sudo tee -a /etc/hosts
echo "127.0.0.1 demo.accesswash.org" | sudo tee -a /etc/hosts
```

### 6. Test Your Setup
```bash
# Start development server
python manage.py runserver

# Test these URLs in browser:
# http://api.accesswash.org:8000/admin/         (Platform admin)
# http://demo.accesswash.org:8000/admin/        (Demo utility admin)
# http://demo.accesswash.org:8000/api/docs/     (API documentation)

# You should see "Distro Field Operations" in demo admin!
```

---

## 🏗️ Project Architecture

### Understanding the Structure
```
accesswash_platform/
├── 🏢 tenants/          → Multi-tenant management (PUBLIC schema)
├── 👥 users/            → Authentication & user roles (BOTH schemas)
├── ⚙️  core/            → Utility settings & branding (TENANT schema)
└── 🗺️  distro/          → Field operations & infrastructure (TENANT schema)

Future modules (v2.0+):
├── 👨‍👩‍👧‍👦 customers/       → Customer management
├── 🎫 huduma/           → Customer support ticketing  
├── 🧪 maji/             → Water quality monitoring
├── 💰 hesabu/           → Billing & payments
└── 📊 analytics/        → Reporting & dashboards
```

### Schema Architecture
- **Public Schema** (`api.accesswash.org`): Platform-level tenant management
- **Tenant Schemas** (`demo.accesswash.org`): Each utility gets isolated data

---

## 💻 Development Workflow

### Daily Development
```bash
# Start your day
cd accesswash-platform
source venv/bin/activate
git pull origin main
python manage.py runserver

# Make changes, test locally
# Commit when ready
git add .
git commit -m "feat: add water quality monitoring"
git push origin feature/your-feature-name

# Create pull request when ready
```

### Working with Database
```bash
# Create new migrations after model changes
python manage.py makemigrations [app_name]

# Apply to shared schema (public)
python manage.py migrate_schemas --shared

# Apply to all tenant schemas
python manage.py migrate_schemas

# Apply to specific tenant
python manage.py migrate_schemas --schema=demo
```

### Testing Your Changes
```bash
# Run tests
python manage.py test

# Test specific app
python manage.py test distro

# Test API endpoints
curl http://demo.accesswash.org:8000/api/distro/assets/
curl http://demo.accesswash.org:8000/api/users/profile/
```

---

## 🎨 Code Style & Standards

### Python Standards
```python
# Use type hints
def create_asset(name: str, location: Point) -> Asset:
    """Create a new water infrastructure asset."""
    return Asset.objects.create(name=name, location=location)

# Use descriptive names
asset_count = Asset.objects.count()  # ✅ Good
n = Asset.objects.count()           # ❌ Bad

# Follow PEP 8
from typing import List, Optional
from django.db import models
from django.contrib.gis.db import models as gis_models
```

### Model Patterns
```python
# Always use TimestampedModel pattern
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

# Use proper spatial fields
class Asset(TimestampedModel):
    location = gis_models.PointField(srid=4326)  # Always use SRID=4326
    
# Use JSON for flexible data
class Asset(TimestampedModel):
    specifications = models.JSONField(default=dict, blank=True)
```

### API Patterns
```python
# ViewSets with proper permissions
class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AssetCreateSerializer
        return AssetSerializer
    
    @action(detail=True, methods=['post'])
    def inspect(self, request, pk=None):
        """Custom endpoint for asset inspection."""
        asset = self.get_object()
        # Implementation here
        return Response({'success': True})
```

---

## 🧪 Testing Guidelines

### Writing Tests
```python
# Use TenantTestCase for tenant-specific tests
from django_tenants.test.cases import TenantTestCase

class AssetTestCase(TenantTestCase):
    def setUp(self):
        self.asset_type = AssetType.objects.create(
            name='Test Type',
            code='test'
        )
    
    def test_asset_creation(self):
        asset = Asset.objects.create(
            name='Test Asset',
            asset_type=self.asset_type,
            location=Point(36.8219, -1.2921)
        )
        self.assertEqual(asset.name, 'Test Asset')
```

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test distro.tests.test_models

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 🔧 Common Development Tasks

### Adding a New Model
```python
# 1. Create model in appropriate app
class WaterMeter(TimestampedModel):
    serial_number = models.CharField(max_length=50, unique=True)
    location = gis_models.PointField(srid=4326)

# 2. Add to admin
@admin.register(WaterMeter)
class WaterMeterAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['serial_number', 'location']

# 3. Create serializer
class WaterMeterSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterMeter
        fields = '__all__'

# 4. Add to ViewSet
class WaterMeterViewSet(viewsets.ModelViewSet):
    queryset = WaterMeter.objects.all()
    serializer_class = WaterMeterSerializer

# 5. Add to URLs
router.register(r'meters', WaterMeterViewSet)
```

### Adding a New API Endpoint
```python
# In views.py
@action(detail=False, methods=['get'])
def nearby_assets(self, request):
    """Find assets near a point."""
    lat = float(request.query_params.get('lat'))
    lng = float(request.query_params.get('lng'))
    radius = int(request.query_params.get('radius', 1000))
    
    point = Point(lng, lat, srid=4326)
    assets = Asset.objects.filter(
        location__distance_lte=(point, D(m=radius))
    ).distance(point).order_by('distance')
    
    serializer = AssetGeoSerializer(assets, many=True)
    return Response(serializer.data)
```

### Working with Spatial Data
```python
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import D

# Create point from coordinates
location = Point(36.8219, -1.2921, srid=4326)

# Find nearby assets
nearby = Asset.objects.filter(
    location__distance_lte=(location, D(m=1000))
)

# Check if point is in zone
zone = Zone.objects.filter(boundary__contains=location).first()
```

---

## 🤝 Contributing Guidelines

### Git Workflow
```bash
# 1. Create feature branch
git checkout -b feature/water-quality-monitoring

# 2. Make changes, commit frequently
git add .
git commit -m "feat: add water quality test model"

# 3. Push to your branch
git push origin feature/water-quality-monitoring

# 4. Create pull request
# 5. After review, merge to main
```

### Commit Message Format
```
type(scope): description

feat(distro): add pipe flow rate calculation
fix(users): resolve login redirect issue  
docs(api): update endpoint documentation
test(distro): add asset creation tests
```

### Pull Request Checklist
- [ ] Tests pass: `python manage.py test`
- [ ] Code follows style guide
- [ ] Documentation updated if needed
- [ ] Migration files included if models changed
- [ ] API endpoints tested manually
- [ ] Admin interface works in demo tenant

---

## 🆘 Getting Help

### Common Issues & Solutions

**Issue**: "Distro not appearing in admin"
```bash
# Solution: Check tenant schema
curl http://demo.accesswash.org:8000/health/
# Should show "Schema: demo"
```

**Issue**: "Migration errors"
```bash
# Solution: Reset migrations
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
python manage.py makemigrations
python manage.py migrate_schemas --shared
```

**Issue**: "Permission denied in admin"
```bash
# Solution: Check user role
python manage.py shell -c "
from users.models import User
user = User.objects.get(email='your@email.com')
print(f'Role: {user.role}, Permissions: {user.get_permissions()}')
"
```

### Team Communication
- **Slack/Discord**: #accesswash-dev channel
- **Issues**: GitHub issues for bugs/features
- **Documentation**: Update this guide when you learn something new!
- **Code Review**: All PRs need review before merge

### Useful Commands
```bash
# Quick reset for development
python manage.py flush --schema=demo  # Clear demo data
python setup_data.py                  # Recreate demo data

# Shell access with tenant context
python manage.py shell
# >>> from django_tenants.utils import schema_context
# >>> with schema_context('demo'):
# ...     from distro.models import Asset
# ...     print(Asset.objects.count())
```

---

**Welcome to the AccessWash team! 🎉 Start with the Quick Start section and you'll be contributing in 15 minutes!**