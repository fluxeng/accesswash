#!/usr/bin/env python
"""
AccessWash Platform - Compact Data Seeding Script
Creates essential demo data for water utility management platform
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
import random
import subprocess

# Colors for console output
class Colors:
   OKGREEN = '\033[92m'
   WARNING = '\033[93m'
   FAIL = '\033[91m'
   ENDC = '\033[0m'
   BOLD = '\033[1m'

def print_success(msg): print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
def print_error(msg): print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")
def print_warning(msg): print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")
def print_step(step, msg): print(f"\n{Colors.BOLD}🚀 Step {step}: {msg}{Colors.ENDC}")

# Configuration
CONFIG = {
   'ADMIN_EMAIL': 'kkimtai@gmail.com',
   'PASSWORD': 'Welcome1!',
   'DEMO_UTILITY': 'Nairobi Water & Sewerage Company',
   'DEMO_DOMAIN': 'demo.accesswash.org'
}

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accesswash_platform.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from django.contrib.gis.geos import Point, Polygon
from django.utils import timezone
from tenants.models import Utility, Domain

User = get_user_model()

class CompactSeeder:
   def __init__(self):
       self.stats = {'tenants': 0, 'users': 0, 'zones': 0, 'assets': 0}
   
   def check_hosts_file(self):
       """Add demo domain to hosts file if not present"""
       hosts_path = '/etc/hosts'
       domain_entry = f"127.0.0.1 {CONFIG['DEMO_DOMAIN']}"
       
       try:
           with open(hosts_path, 'r') as f:
               content = f.read()
           
           if CONFIG['DEMO_DOMAIN'] not in content:
               print_warning(f"Adding {CONFIG['DEMO_DOMAIN']} to hosts file")
               try:
                   subprocess.run(['sudo', 'sh', '-c', f'echo "{domain_entry}" >> {hosts_path}'], 
                                check=True, capture_output=True)
                   print_success("Updated hosts file")
               except subprocess.CalledProcessError:
                   print_warning(f"Please manually add: {domain_entry} to {hosts_path}")
           else:
               print_success("Hosts file already configured")
       except Exception:
           print_warning(f"Please add manually: {domain_entry} to {hosts_path}")
   
   def seed_tenants(self):
       print_step(1, "Creating Tenants & Domains")
       
       # Public tenant
       public_tenant, created = Utility.objects.get_or_create(
           schema_name='public',
           defaults={'name': 'AccessWash Platform', 'is_active': True}
       )
       if created: self.stats['tenants'] += 1
       
       # Localhost domain
       Domain.objects.get_or_create(
           domain='localhost', tenant=public_tenant,
           defaults={'is_primary': True, 'is_active': True}
       )
       
       # Demo tenant
       demo_tenant, created = Utility.objects.get_or_create(
           schema_name='demo',
           defaults={'name': CONFIG['DEMO_UTILITY'], 'is_active': True}
       )
       if created:
           self.stats['tenants'] += 1
           call_command('migrate_schemas', '--schema=demo', verbosity=0)
       
       # Demo domain
       Domain.objects.get_or_create(
           domain=CONFIG['DEMO_DOMAIN'], tenant=demo_tenant,
           defaults={'is_primary': True, 'is_active': True}
       )
       
       print_success(f"Created {self.stats['tenants']} tenants")
   
   def seed_users(self):
       print_step(2, "Creating Users")
       
       # Platform admin
       admin, created = User.objects.get_or_create(
           email=CONFIG['ADMIN_EMAIL'],
           defaults={
               'first_name': 'Ken', 'last_name': 'Ruto',
               'role': User.ADMIN, 'is_staff': True, 'is_superuser': True
           }
       )
       if created:
           admin.set_password(CONFIG['PASSWORD'])
           admin.save()
           self.stats['users'] += 1
       
       # Demo utility users
       demo_users = [
           {'email': 'demo1@accesswash.org', 'first_name': 'Demo', 'last_name': 'Account', 'role': User.ADMIN, 'is_superuser': True},
           {'email': 'supervisor@nairobidemo.accesswash.org', 'first_name': 'John', 'last_name': 'Mwangi', 'role': User.SUPERVISOR},
           {'email': 'field1@nairobidemo.accesswash.org', 'first_name': 'Peter', 'last_name': 'Otieno', 'role': User.FIELD_TECH},
           {'email': 'field2@nairobidemo.accesswash.org', 'first_name': 'Grace', 'last_name': 'Wanjiku', 'role': User.FIELD_TECH},
           {'email': 'support@nairobidemo.accesswash.org', 'first_name': 'David', 'last_name': 'Kiprop', 'role': User.CUSTOMER_SERVICE}
       ]
       
       with schema_context('demo'):
           for user_data in demo_users:
               user, created = User.objects.get_or_create(
                   email=user_data['email'], defaults=user_data
               )
               if created:
                   user.set_password(CONFIG['PASSWORD'])
                   user.save()
                   self.stats['users'] += 1
       
       print_success(f"Created {self.stats['users']} users")
   
   def seed_core_data(self):
       print_step(3, "Setting Up Utility Configuration")
       
       with schema_context('demo'):
           from core.models import UtilitySettings
           
           UtilitySettings.objects.get_or_create(
               defaults={
                   'utility_name': CONFIG['DEMO_UTILITY'],
                   'primary_color': '#1565C0',
                   'secondary_color': '#2E7D32',
                   'contact_phone': '+254 20 4452000',
                   'contact_email': 'info@nairobiwter.co.ke',
                   'address': 'Norfolk Towers, Nairobi, Kenya',
                   'distro_enabled': True
               }
           )
       
       print_success("Configured utility settings")
   
   def seed_infrastructure(self):
       print_step(4, "Creating Infrastructure Data")
       
       with schema_context('demo'):
           from distro.models import AssetType, Zone, Asset, Pipe, Valve, Meter
           
           # Asset types
           asset_types = [
               {'name': 'Water Pipe', 'code': 'pipe', 'icon': 'pipe', 'color': '#2563EB', 'is_linear': True},
               {'name': 'Valve', 'code': 'valve', 'icon': 'valve', 'color': '#DC2626', 'is_linear': False},
               {'name': 'Water Meter', 'code': 'meter', 'icon': 'meter', 'color': '#059669', 'is_linear': False},
               {'name': 'Pump Station', 'code': 'pump_station', 'icon': 'pump', 'color': '#7C3AED', 'is_linear': False},
               {'name': 'Reservoir', 'code': 'reservoir', 'icon': 'reservoir', 'color': '#0891B2', 'is_linear': False}
           ]
           
           for at_data in asset_types:
               AssetType.objects.get_or_create(code=at_data['code'], defaults=at_data)
           
           # Zones
           zones_data = [
               {
                   'name': 'Westlands Zone', 'code': 'WL001',
                   'boundary': Polygon([[36.79, -1.27], [36.82, -1.27], [36.82, -1.24], [36.79, -1.24], [36.79, -1.27]]),
                   'population': 45000, 'households': 11250
               },
               {
                   'name': 'Karen Zone', 'code': 'KR001', 
                   'boundary': Polygon([[36.68, -1.33], [36.72, -1.33], [36.72, -1.30], [36.68, -1.30], [36.68, -1.33]]),
                   'population': 25000, 'households': 6250
               },
               {
                   'name': 'Industrial Area', 'code': 'IA001',
                   'boundary': Polygon([[36.85, -1.31], [36.88, -1.31], [36.88, -1.28], [36.85, -1.28], [36.85, -1.31]]),
                   'population': 8000, 'households': 2000
               }
           ]
           
           zones = {}
           for zone_data in zones_data:
               zone, created = Zone.objects.get_or_create(code=zone_data['code'], defaults=zone_data)
               zones[zone_data['code']] = zone
               if created: self.stats['zones'] += 1
           
           # Assets
           pipe_type = AssetType.objects.get(code='pipe')
           valve_type = AssetType.objects.get(code='valve')
           meter_type = AssetType.objects.get(code='meter')
           pump_type = AssetType.objects.get(code='pump_station')
           reservoir_type = AssetType.objects.get(code='reservoir')
           
           # Major assets
           major_assets = [
               {
                   'name': 'Gigiri Treatment Plant',
                   'asset_type': pump_type,
                   'location': Point(36.8219, -1.2521),
                   'zone': zones['WL001'],
                   'status': 'operational',
                   'condition': 4
               },
               {
                   'name': 'Karen Reservoir',
                   'asset_type': reservoir_type,
                   'location': Point(36.7076, -1.3197),
                   'zone': zones['KR001'],
                   'status': 'operational',
                   'condition': 5
               },
               {
                   'name': 'Industrial Pump Station',
                   'asset_type': pump_type,
                   'location': Point(36.8600, -1.2950),
                   'zone': zones['IA001'],
                   'status': 'operational',
                   'condition': 3
               }
           ]
           
           for asset_data in major_assets:
               asset, created = Asset.objects.get_or_create(
                   name=asset_data['name'], defaults=asset_data
               )
               if created: self.stats['assets'] += 1
           
           # Sample pipes, valves, meters
           coords = [(-1.2641, 36.8078), (-1.3197, 36.7076), (-1.2950, 36.8600)]
           
           for i, (lat, lng) in enumerate(coords):
               zone = list(zones.values())[i]
               
               # Valves
               for j in range(3):
                   valve_asset = Asset.objects.create(
                       name=f'{zone.name} Valve {j+1}',
                       asset_type=valve_type,
                       location=Point(lng + random.uniform(-0.01, 0.01), lat + random.uniform(-0.01, 0.01)),
                       zone=zone,
                       status='operational',
                       condition=random.randint(3, 5)
                   )
                   Valve.objects.create(
                       asset=valve_asset,
                       valve_type=random.choice(['gate', 'ball', 'butterfly']),
                       diameter=random.choice([100, 150, 200]),
                       is_open=True
                   )
                   self.stats['assets'] += 1
               
               # Meters
               for j in range(3):
                   meter_asset = Asset.objects.create(
                       name=f'{zone.name} Meter {j+1}',
                       asset_type=meter_type,
                       location=Point(lng + random.uniform(-0.02, 0.02), lat + random.uniform(-0.02, 0.02)),
                       zone=zone,
                       status='operational',
                       condition=random.randint(3, 5)
                   )
                   Meter.objects.create(
                       asset=meter_asset,
                       meter_type='customer',
                       serial_number=f'MTR{2024}{random.randint(10000, 99999)}',
                       size=random.choice([15, 20, 25]),
                       brand=random.choice(['Sensus', 'Kamstrup', 'Itron'])
                   )
                   self.stats['assets'] += 1
       
       print_success(f"Created {self.stats['zones']} zones and {self.stats['assets']} assets")
   
   def seed_operational_data(self):
       print_step(5, "Adding Operational Data")
       
       with schema_context('demo'):
           from distro.models import Asset, AssetInspection
           
           # Get some assets for inspections
           assets = Asset.objects.all()[:10]
           field_users = User.objects.filter(role=User.FIELD_TECH)
           
           inspections_created = 0
           for asset in assets:
               for i in range(2):  # 2 inspections per asset
                   inspection_date = timezone.now() - timedelta(days=random.randint(1, 90))
                   AssetInspection.objects.get_or_create(
                       asset=asset,
                       inspection_date=inspection_date,
                       defaults={
                           'inspector': random.choice(field_users) if field_users else None,
                           'condition_rating': random.randint(3, 5),
                           'notes': f'Routine inspection - {asset.name} in good condition',
                           'requires_maintenance': random.choice([True, False])
                       }
                   )
                   inspections_created += 1
       
       print_success(f"Created {inspections_created} inspection records")
   
   def run_seeding(self):
       print(f"\n{Colors.BOLD}🚀 AccessWash Platform Data Seeding{Colors.ENDC}")
       print("=" * 50)
       
       try:
           self.check_hosts_file()
           self.seed_tenants()
           self.seed_users() 
           self.seed_core_data()
           self.seed_infrastructure()
           self.seed_operational_data()
           
           print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 Seeding Complete!{Colors.ENDC}")
           print("\n📊 Summary:")
           print(f"• Tenants: {self.stats['tenants']}")
           print(f"• Users: {self.stats['users']}")
           print(f"• Zones: {self.stats['zones']}")
           print(f"• Assets: {self.stats['assets']}")
           
           print(f"\n🌐 Access Points:")
           print(f"• Platform: http://localhost:8000/admin/")
           print(f"• Demo Utility: http://{CONFIG['DEMO_DOMAIN']}:8000/admin/")
           print(f"• API Docs: http://{CONFIG['DEMO_DOMAIN']}:8000/api/docs/")
           
           print(f"\n👤 Login Credentials:")
           print(f"• Platform Admin: {CONFIG['ADMIN_EMAIL']} / {CONFIG['PASSWORD']}")
           print(f"• Demo Manager: manager@nairobidemo.accesswash.org / {CONFIG['PASSWORD']}")
           print(f"• Field Tech: field1@nairobidemo.accesswash.org / {CONFIG['PASSWORD']}")
           
           print(f"\n🚀 Next Steps:")
           print(f"1. Start server: python manage.py runserver")
           print(f"2. Visit: http://{CONFIG['DEMO_DOMAIN']}:8000/admin/")
           
       except Exception as e:
           print_error(f"Seeding failed: {str(e)}")
           import traceback
           traceback.print_exc()
           return False
       
       return True

if __name__ == "__main__":
   seeder = CompactSeeder()
   success = seeder.run_seeding()
   sys.exit(0 if success else 1)