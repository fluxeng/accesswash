#!/usr/bin/env python
"""
AccessWash Platform Demo Data Setup - FIXED VERSION
Creates comprehensive demo data for the AccessWash water utility platform
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
from decimal import Decimal
import random

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_step(step, message):
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}🚀 Step {step}: {message}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.OKBLUE}ℹ️  {message}{Colors.ENDC}")

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accesswash_platform.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from django.contrib.gis.geos import Point, Polygon, LineString
from tenants.models import Utility, Domain

User = get_user_model()

def setup_tenants():
    """Create tenants and domains using only existing fields"""
    print_step(1, "Setting Up Tenants & Domains")
    
    # Create public tenant - use only fields that exist in your model
    public_tenant, created = Utility.objects.get_or_create(
        schema_name='public',
        defaults={
            'name': 'AccessWash Platform',
            'is_active': True
        }
    )
    
    if created:
        print_success("Created public tenant")
    
    # Create localhost domain
    localhost_domain, created = Domain.objects.get_or_create(
        domain='localhost',
        tenant=public_tenant,
        defaults={'is_primary': True, 'is_active': True}
    )
    
    if created:
        print_success("Created localhost domain")
    
    # Create demo utility
    demo_tenant, created = Utility.objects.get_or_create(
        schema_name='demo',
        defaults={
            'name': 'Nairobi Demo Water Company',
            'is_active': True
        }
    )
    
    if created:
        print_success("Created demo tenant")
        # Migrate demo tenant
        call_command('migrate_schemas', '--schema=demo', verbosity=0)
        print_success("Demo tenant migrations completed")
    
    # Create demo domain
    demo_domain, created = Domain.objects.get_or_create(
        domain='demo.accesswash.org',
        tenant=demo_tenant,
        defaults={'is_primary': True, 'is_active': True}
    )
    
    if created:
        print_success("Created demo.accesswash.org domain")

def setup_demo_data():
    """Create comprehensive demo data for demo tenant"""
    print_step(2, "Creating Demo Data for Nairobi Demo Water Company")
    
    with schema_context('demo'):
        # Check if core app models exist, if not skip
        try:
            from core.models import UtilitySettings
            has_core = True
        except ImportError:
            print_info("Core app not available, skipping utility settings")
            has_core = False
        
        try:
            from distro.models import AssetType, Zone, Asset, Pipe, Valve, Meter, AssetPhoto, AssetInspection
            has_distro = True
        except ImportError:
            print_error("Distro app not available, cannot create infrastructure data")
            return False
        
        try:
            from customers.models import Customer, ServiceRequest, CustomerBill
            has_customers = True
        except ImportError:
            print_info("Customers app not available, skipping customer data")
            has_customers = False
        
        # Create utility settings if core app exists
        if has_core:
            utility_settings, created = UtilitySettings.objects.get_or_create(
                defaults={
                    'utility_name': 'Nairobi Demo Water Company',
                    'primary_color': '#1e40af',
                    'secondary_color': '#3b82f6',
                    'contact_phone': '+254 700 123 456',
                    'contact_email': 'info@nairobidemo.accesswash.org',
                    'website': 'https://nairobidemo.accesswash.org',
                    'address': '123 Water Works Road, Nairobi, Kenya',
                    'distro_enabled': True,
                }
            )
            if created:
                print_success("Created utility settings")
        
        # Create asset types
        asset_types_data = [
            {'name': 'Water Pipe', 'code': 'pipe', 'icon': 'pipe-icon', 'color': '#2563eb', 'is_linear': True},
            {'name': 'Valve', 'code': 'valve', 'icon': 'valve-icon', 'color': '#dc2626', 'is_linear': False},
            {'name': 'Water Meter', 'code': 'meter', 'icon': 'meter-icon', 'color': '#059669', 'is_linear': False},
            {'name': 'Pump Station', 'code': 'pump_station', 'icon': 'pump-icon', 'color': '#7c3aed', 'is_linear': False},
            {'name': 'Reservoir', 'code': 'reservoir', 'icon': 'reservoir-icon', 'color': '#0891b2', 'is_linear': False},
            {'name': 'Treatment Plant', 'code': 'treatment_plant', 'icon': 'plant-icon', 'color': '#ea580c', 'is_linear': False},
            {'name': 'Fire Hydrant', 'code': 'hydrant', 'icon': 'hydrant-icon', 'color': '#be123c', 'is_linear': False},
            {'name': 'Booster Station', 'code': 'booster', 'icon': 'booster-icon', 'color': '#8b5cf6', 'is_linear': False},
        ]
        
        created_types = 0
        for asset_data in asset_types_data:
            asset_type, created = AssetType.objects.get_or_create(
                code=asset_data['code'],
                defaults=asset_data
            )
            if created:
                created_types += 1
        
        print_success(f"Created {created_types} asset types")
        
        # Create zones (Nairobi areas)
        zones_data = [
            {
                'name': 'Westlands Zone',
                'code': 'WL001',
                'boundary': Polygon([
                    [36.80, -1.26], [36.82, -1.26], [36.82, -1.24], [36.80, -1.24], [36.80, -1.26]
                ]),
                'population': 45000,
                'households': 11250,
                'commercial_connections': 650,
            },
            {
                'name': 'Karen Zone',
                'code': 'KR001',
                'boundary': Polygon([
                    [36.68, -1.32], [36.72, -1.32], [36.72, -1.30], [36.68, -1.30], [36.68, -1.32]
                ]),
                'population': 25000,
                'households': 6250,
                'commercial_connections': 180,
            },
            {
                'name': 'Industrial Area',
                'code': 'IA001',
                'boundary': Polygon([
                    [36.85, -1.30], [36.88, -1.30], [36.88, -1.28], [36.85, -1.28], [36.85, -1.30]
                ]),
                'population': 8000,
                'households': 2000,
                'commercial_connections': 890,
            },
            {
                'name': 'Kilimani Zone',
                'code': 'KM001',
                'boundary': Polygon([
                    [36.78, -1.29], [36.81, -1.29], [36.81, -1.27], [36.78, -1.27], [36.78, -1.29]
                ]),
                'population': 32000,
                'households': 8000,
                'commercial_connections': 420,
            },
            {
                'name': 'Kibera Zone',
                'code': 'KB001',
                'boundary': Polygon([
                    [36.76, -1.31], [36.78, -1.31], [36.78, -1.29], [36.76, -1.29], [36.76, -1.31]
                ]),
                'population': 185000,
                'households': 37000,
                'commercial_connections': 150,
            }
        ]
        
        created_zones = 0
        zones = {}
        for zone_data in zones_data:
            zone, created = Zone.objects.get_or_create(
                code=zone_data['code'],
                defaults=zone_data
            )
            if created:
                created_zones += 1
            zones[zone_data['code']] = zone
        
        print_success(f"Created {created_zones} zones")
        
        # Create sample assets
        print_info("Creating sample assets...")
        
        # Get asset types
        pipe_type = AssetType.objects.get(code='pipe')
        valve_type = AssetType.objects.get(code='valve')
        meter_type = AssetType.objects.get(code='meter')
        pump_type = AssetType.objects.get(code='pump_station')
        reservoir_type = AssetType.objects.get(code='reservoir')
        
        # Sample coordinates around Nairobi
        nairobi_coords = [
            (-1.2921, 36.8219),  # CBD
            (-1.2641, 36.8078),  # Westlands
            (-1.3197, 36.7076),  # Karen
            (-1.3031, 36.8523),  # Industrial Area
            (-1.2833, 36.8167),  # Kilimani
            (-1.3133, 36.7833),  # Kibera
        ]
        
        assets_created = 0
        
        # Create major infrastructure
        major_assets = [
            {
                'name': 'Gigiri Water Treatment Plant',
                'asset_type': reservoir_type,
                'location': Point(36.8219, -1.2521),
                'zone': zones['WL001'],
                'status': 'operational',
                'condition': 4,
                'specifications': {
                    'capacity': '50,000 m³/day',
                    'treatment_type': 'Conventional',
                    'commissioned': '2019'
                }
            },
            {
                'name': 'Westlands Pump Station A',
                'asset_type': pump_type,
                'location': Point(36.8078, -1.2641),
                'zone': zones['WL001'],
                'status': 'operational',
                'condition': 4,
                'specifications': {
                    'capacity': '5,000 m³/day',
                    'pump_type': 'Centrifugal',
                    'power': '50 kW'
                }
            },
            {
                'name': 'Karen Reservoir',
                'asset_type': reservoir_type,
                'location': Point(36.7076, -1.3197),
                'zone': zones['KR001'],
                'status': 'operational',
                'condition': 5,
                'specifications': {
                    'capacity': '10,000 m³',
                    'material': 'Concrete',
                    'height': '15 m'
                }
            }
        ]
        
        for asset_data in major_assets:
            asset, created = Asset.objects.get_or_create(
                name=asset_data['name'],
                defaults=asset_data
            )
            if created:
                assets_created += 1
        
        # Create distribution network
        for i, (lat, lng) in enumerate(nairobi_coords):
            zone_code = list(zones.keys())[i % len(zones)]
            zone = zones[zone_code]
            
            # Create valves
            for j in range(3):
                valve_asset = Asset.objects.create(
                    name=f'{zone.name} Main Valve {j+1}',
                    asset_type=valve_type,
                    location=Point(lng + random.uniform(-0.01, 0.01), lat + random.uniform(-0.01, 0.01)),
                    zone=zone,
                    status=random.choice(['operational', 'maintenance']),
                    condition=random.randint(3, 5),
                    installation_date=date(2020, random.randint(1, 12), random.randint(1, 28)),
                    specifications={'diameter': f'{random.choice([100, 150, 200, 300])}mm'}
                )
                
                # Create valve details
                Valve.objects.create(
                    asset=valve_asset,
                    valve_type=random.choice(['gate', 'ball', 'butterfly']),
                    diameter=random.choice([100, 150, 200, 300]),
                    is_open=random.choice([True, False]),
                    is_automated=random.choice([True, False]),
                    turns_to_close=random.randint(10, 50)
                )
                assets_created += 1
            
            # Create meters
            for j in range(5):
                meter_asset = Asset.objects.create(
                    name=f'{zone.name} Meter {j+1:03d}',
                    asset_type=meter_type,
                    location=Point(lng + random.uniform(-0.02, 0.02), lat + random.uniform(-0.02, 0.02)),
                    zone=zone,
                    status='operational',
                    condition=random.randint(3, 5),
                    installation_date=date(2021, random.randint(1, 12), random.randint(1, 28)),
                    specifications={'size': f'{random.choice([15, 20, 25, 32])}mm'}
                )
                
                # Create meter details
                Meter.objects.create(
                    asset=meter_asset,
                    meter_type=random.choice(['mechanical', 'digital', 'smart']),
                    serial_number=f'MTR{2024}{random.randint(10000, 99999)}',
                    size=random.choice([15, 20, 25, 32]),
                    brand=random.choice(['Sensus', 'Kamstrup', 'Itron', 'Neptune']),
                    model=f'Model-{random.randint(100, 999)}',
                    last_reading=random.uniform(1000, 5000),
                    last_reading_date=datetime.now() - timedelta(days=random.randint(1, 30))
                )
                assets_created += 1
        
        print_success(f"Created {assets_created} assets")
        
        # Create customers only if customers app exists
        if has_customers:
            print_info("Creating customer accounts...")
            
            customer_names = [
                'John Kamau', 'Mary Wanjiku', 'Peter Otieno', 'Grace Akinyi', 'David Kiprop',
                'Sarah Nyong\'o', 'Michael Mwangi', 'Faith Chebet', 'Samuel Ochieng', 'Ruth Muthoni',
                'James Karanja', 'Jane Awuor', 'Robert Kiprotich', 'Helen Wairimu', 'Daniel Omondi',
                'Lucy Wambui', 'Thomas Koech', 'Agnes Nafula', 'Francis Njoroge', 'Esther Auma',
                'Nairobi Breweries Ltd', 'Safaricom House', 'KCB Bank', 'Equity Bank', 'Nation Media Group',
                'Bidco Oil Refineries', 'East African Cables', 'Kenya Airways', 'Bamburi Cement', 'NCBA Bank'
            ]
            
            addresses = [
                'Kileleshwa Road, Nairobi', 'Parklands Avenue, Nairobi', 'Lavington Green, Nairobi',
                'Kilimani Road, Nairobi', 'Riverside Drive, Nairobi', 'Karen Road, Nairobi',
                'Industrial Area Road, Nairobi', 'Westlands Road, Nairobi', 'Hurlingham Road, Nairobi',
                'Runda Estate, Nairobi', 'Spring Valley Road, Nairobi', 'Muthaiga Road, Nairobi'
            ]
            
            customers_created = 0
            for i, name in enumerate(customer_names):
                is_commercial = i >= 20  # Last 10 are commercial
                
                customer = Customer.objects.create(
                    account_number=f'ACC{2024}{i+1:04d}',
                    name=name,
                    email=f'customer{i+1}@email.com' if not is_commercial else f'billing{i+1}@company.com',
                    phone=f'+254{random.randint(700000000, 799999999)}',
                    address=random.choice(addresses),
                    location=Point(
                        36.8219 + random.uniform(-0.1, 0.1),
                        -1.2921 + random.uniform(-0.1, 0.1)
                    ),
                    customer_type='commercial' if is_commercial else 'residential',
                    status=random.choice(['active', 'active', 'active', 'suspended']) if i % 10 != 0 else 'pending',
                    connection_date=date(2020, random.randint(1, 12), random.randint(1, 28)),
                    billing_cycle='monthly'
                )
                customers_created += 1
            
            print_success(f"Created {customers_created} customers")
        
        return True

def create_users():
    """Create users for different tenants"""
    print_step(3, "Creating Users")
    
    # Create platform admin (public schema)
    try:
        platform_admin = User.objects.create_superuser(
            email='admin@accesswash.org',
            password='AccessWash2024!',
            first_name='Platform',
            last_name='Administrator',
            role='admin'
        )
        print_success("Created platform administrator")
    except:
        print_info("Platform administrator already exists")
    
    # Create demo utility users
    with schema_context('demo'):
        demo_users = [
            {
                'email': 'manager@nairobidemo.accesswash.org',
                'password': 'Demo2024!',
                'first_name': 'Sarah',
                'last_name': 'Kimani',
                'role': 'admin',
                'is_superuser': True
            },
            {
                'email': 'supervisor@nairobidemo.accesswash.org', 
                'password': 'Demo2024!',
                'first_name': 'John',
                'last_name': 'Mwangi',
                'role': 'supervisor'
            },
            {
                'email': 'field1@nairobidemo.accesswash.org',
                'password': 'Demo2024!',
                'first_name': 'Peter',
                'last_name': 'Otieno',
                'role': 'field_tech'
            },
            {
                'email': 'field2@nairobidemo.accesswash.org',
                'password': 'Demo2024!',
                'first_name': 'Grace',
                'last_name': 'Wanjiku',
                'role': 'field_tech'
            },
            {
                'email': 'support@nairobidemo.accesswash.org',
                'password': 'Demo2024!',
                'first_name': 'David',
                'last_name': 'Kiprop',
                'role': 'customer_service'
            }
        ]
        
        users_created = 0
        for user_data in demo_users:
            try:
                if user_data.get('is_superuser'):
                    user = User.objects.create_superuser(
                        email=user_data['email'],
                        password=user_data['password'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        role=user_data['role']
                    )
                else:
                    user = User.objects.create_user(
                        email=user_data['email'],
                        password=user_data['password'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        role=user_data['role']
                    )
                users_created += 1
            except:
                print_info(f"User {user_data['email']} already exists")
        
        print_success(f"Created {users_created} demo utility users")

def print_summary():
    """Print setup summary with access information"""
    print_step(4, "Setup Complete! 🎉")
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}AccessWash Platform Demo Data Created{Colors.ENDC}")
    print(f"{Colors.HEADER}={'='*50}{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}🌐 Access Points:{Colors.ENDC}")
    print(f"• Platform Admin: {Colors.OKBLUE}http://localhost:8000/admin/{Colors.ENDC}")
    print(f"• Platform API: {Colors.OKBLUE}http://localhost:8000/api/docs/{Colors.ENDC}")
    print(f"• Demo Utility: {Colors.OKBLUE}http://demo.accesswash.org:8000/admin/{Colors.ENDC}")
    print(f"• Demo API: {Colors.OKBLUE}http://demo.accesswash.org:8000/api/docs/{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}👤 Login Credentials:{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}Platform Administrator:{Colors.ENDC}")
    print(f"  Email: admin@accesswash.org")
    print(f"  Password: AccessWash2024!")
    
    print(f"\n{Colors.OKCYAN}Demo Utility Users:{Colors.ENDC}")
    print(f"  Manager: manager@nairobidemo.accesswash.org / Demo2024!")
    print(f"  Supervisor: supervisor@nairobidemo.accesswash.org / Demo2024!")
    print(f"  Field Tech 1: field1@nairobidemo.accesswash.org / Demo2024!")
    print(f"  Field Tech 2: field2@nairobidemo.accesswash.org / Demo2024!")
    print(f"  Customer Support: support@nairobidemo.accesswash.org / Demo2024!")
    
    print(f"\n{Colors.BOLD}🚀 Next Steps:{Colors.ENDC}")
    print(f"1. Add to /etc/hosts: {Colors.WARNING}127.0.0.1 demo.accesswash.org{Colors.ENDC}")
    print(f"2. Start server: {Colors.OKCYAN}python manage.py runserver{Colors.ENDC}")
    print(f"3. Explore the admin interfaces and APIs")
    print(f"4. Test different user roles and permissions")
    
    print(f"\n{Colors.OKGREEN}✅ AccessWash platform is ready for development and demo!{Colors.ENDC}")

def main():
    """Main setup function"""
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}AccessWash Platform Demo Data Setup{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    
    try:
        setup_tenants()
        setup_demo_data()
        create_users()
        print_summary()
        
    except Exception as e:
        print_error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()