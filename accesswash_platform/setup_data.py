#!/usr/bin/env python
"""
AccessWash Platform - Complete Data Seeding Script
Creates essential demo data for water utility management platform
Including customer portal data and service requests
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
       self.stats = {
           'tenants': 0, 
           'users': 0, 
           'zones': 0, 
           'assets': 0,
           'customers': 0,
           'service_requests': 0,
           'comments': 0,
           'photos': 0,
           'inspections': 0
       }
   
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
       print_step(2, "Creating Staff Users")
       
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
       
       # Demo utility staff users
       demo_users = [
           {'email': 'demo1@accesswash.org', 'first_name': 'Demo', 'last_name': 'Account', 'role': User.ADMIN, 'is_superuser': True, 'is_staff': True},
           {'email': 'manager@nairobidemo.accesswash.org', 'first_name': 'Sarah', 'last_name': 'Johnson', 'role': User.ADMIN, 'is_superuser': True, 'is_staff': True},
           {'email': 'supervisor@nairobidemo.accesswash.org', 'first_name': 'John', 'last_name': 'Mwangi', 'role': User.SUPERVISOR, 'is_staff': True},
           {'email': 'field1@nairobidemo.accesswash.org', 'first_name': 'Peter', 'last_name': 'Otieno', 'role': User.FIELD_TECH},
           {'email': 'field2@nairobidemo.accesswash.org', 'first_name': 'Grace', 'last_name': 'Wanjiku', 'role': User.FIELD_TECH},
           {'email': 'field3@nairobidemo.accesswash.org', 'first_name': 'James', 'last_name': 'Mutua', 'role': User.FIELD_TECH},
           {'email': 'support1@nairobidemo.accesswash.org', 'first_name': 'David', 'last_name': 'Kiprop', 'role': User.CUSTOMER_SERVICE},
           {'email': 'support2@nairobidemo.accesswash.org', 'first_name': 'Mary', 'last_name': 'Achieng', 'role': User.CUSTOMER_SERVICE}
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
       
       print_success(f"Created {self.stats['users']} staff users")
   
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
                   meter = Meter.objects.create(
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
                   inspection, created = AssetInspection.objects.get_or_create(
                       asset=asset,
                       inspection_date=inspection_date,
                       defaults={
                           'inspector': random.choice(field_users) if field_users else None,
                           'condition_rating': random.randint(3, 5),
                           'notes': f'Routine inspection - {asset.name} in good condition',
                           'requires_maintenance': random.choice([True, False])
                       }
                   )
                   if created:
                       inspections_created += 1
           
           self.stats['inspections'] = inspections_created
       
       print_success(f"Created {inspections_created} inspection records")
   
   def seed_customer_data(self):
       print_step(6, "Creating Customer Portal Data")
       
       with schema_context('demo'):
           from portal.models import Customer
           from distro.models import Meter
           
           # Get some meters to link to customers
           meters = list(Meter.objects.all()[:8])
           
           # Create sample customers
           customers_data = [
               {
                   'email': 'john.doe@example.com',
                   'first_name': 'John',
                   'last_name': 'Doe',
                   'phone_number': '+254701234567',
                   'property_address': 'Westlands Square, Block A, Apt 12, Nairobi',
                   'service_type': 'residential',
                   'connection_date': date(2020, 3, 15),
                   'meter': meters[0] if meters else None
               },
               {
                   'email': 'mary.wanjiku@example.com',
                   'first_name': 'Mary',
                   'last_name': 'Wanjiku',
                   'phone_number': '+254712345678',
                   'property_address': 'Karen Estate, House No. 45, Karen, Nairobi',
                   'service_type': 'residential',
                   'connection_date': date(2019, 8, 22),
                   'meter': meters[1] if len(meters) > 1 else None
               },
               {
                   'email': 'peter.kamau@businesscorp.co.ke',
                   'first_name': 'Peter',
                   'last_name': 'Kamau',
                   'phone_number': '+254723456789',
                   'property_address': 'Industrial Area, Building C, Factory 5, Nairobi',
                   'service_type': 'commercial',
                   'connection_date': date(2018, 11, 10),
                   'meter': meters[2] if len(meters) > 2 else None
               },
               {
                   'email': 'grace.njeri@gmail.com',
                   'first_name': 'Grace',
                   'last_name': 'Njeri',
                   'phone_number': '+254734567890',
                   'property_address': 'Kileleshwa, Mandera Road, House 23, Nairobi',
                   'service_type': 'residential',
                   'connection_date': date(2021, 1, 8),
                   'meter': meters[3] if len(meters) > 3 else None
               },
               {
                   'email': 'david.ochieng@company.com',
                   'first_name': 'David',
                   'last_name': 'Ochieng',
                   'phone_number': '+254745678901',
                   'property_address': 'Westlands, Chiromo Lane, Office Block 7, Nairobi',
                   'service_type': 'commercial',
                   'connection_date': date(2022, 6, 14),
                   'meter': meters[4] if len(meters) > 4 else None
               },
               {
                   'email': 'jane.muthoni@email.com',
                   'first_name': 'Jane',
                   'last_name': 'Muthoni',
                   'phone_number': '+254756789012',
                   'property_address': 'Lavington, Green Park Estate, House 18, Nairobi',
                   'service_type': 'residential',
                   'connection_date': date(2020, 9, 3),
                   'meter': meters[5] if len(meters) > 5 else None
               },
               {
                   'email': 'samuel.kiprop@institution.org',
                   'first_name': 'Samuel',
                   'last_name': 'Kiprop',
                   'phone_number': '+254767890123',
                   'property_address': 'University of Nairobi, Main Campus, Admin Block',
                   'service_type': 'institutional',
                   'connection_date': date(2017, 4, 20),
                   'meter': meters[6] if len(meters) > 6 else None
               },
               {
                   'email': 'alice.waweru@home.com',
                   'first_name': 'Alice',
                   'last_name': 'Waweru',
                   'phone_number': '+254778901234',
                   'property_address': 'Kilimani, Ralph Bunche Road, Apartment 4B, Nairobi',
                   'service_type': 'residential',
                   'connection_date': date(2023, 2, 12),
                   'meter': meters[7] if len(meters) > 7 else None
               }
           ]
           
           customers = []
           for customer_data in customers_data:
               customer, created = Customer.objects.get_or_create(
                   email=customer_data['email'],
                   defaults=customer_data
               )
               if created:
                   customer.set_password(CONFIG['PASSWORD'])
                   customer.email_verified = True
                   customer.phone_verified = True
                   customer.save()
                   customers.append(customer)
                   self.stats['customers'] += 1
               else:
                   customers.append(customer)
           
           print_success(f"Created {self.stats['customers']} customers")
           return customers
   
   def seed_service_requests(self, customers):
       print_step(7, "Creating Service Requests & Support Data")
       
       with schema_context('demo'):
           from support.models import ServiceRequest, ServiceRequestComment
           from distro.models import Asset
           
           # Get staff users for assignments
           field_users = list(User.objects.filter(role=User.FIELD_TECH))
           support_users = list(User.objects.filter(role=User.CUSTOMER_SERVICE))
           all_staff = field_users + support_users
           
           # Get some assets for related issues
           assets = list(Asset.objects.all()[:5])
           
           # Service request templates
           service_requests_data = [
               {
                   'customer': customers[0],
                   'issue_type': 'no_water',
                   'title': 'No water supply since morning',
                   'description': 'There has been no water supply in our area since 6 AM today. The entire building is affected.',
                   'urgency': 'high',
                   'reported_location': 'Westlands Square, Block A - entire building affected',
                   'status': 'assigned',
                   'related_asset': assets[0] if assets else None,
                   'days_ago': 2
               },
               {
                   'customer': customers[1], 
                   'issue_type': 'low_pressure',
                   'title': 'Very low water pressure for past week',
                   'description': 'Water pressure has been extremely low for the past week. It takes forever to fill a bucket.',
                   'urgency': 'standard',
                   'reported_location': 'Karen Estate, House No. 45 - main supply line',
                   'status': 'in_progress',
                   'related_asset': assets[1] if len(assets) > 1 else None,
                   'days_ago': 5
               },
               {
                   'customer': customers[2],
                   'issue_type': 'meter_problem',
                   'title': 'Water meter not recording correctly',
                   'description': 'The water meter appears to be stuck and not recording usage accurately for the past month.',
                   'urgency': 'standard',
                   'reported_location': 'Industrial Area, Building C - meter box outside',
                   'status': 'resolved',
                   'related_asset': customers[2].meter.asset if customers[2].meter else None,
                   'days_ago': 8
               },
               {
                   'customer': customers[3],
                   'issue_type': 'pipe_burst',
                   'title': 'Pipe burst in compound',
                   'description': 'There is a burst pipe in our compound causing water wastage and flooding.',
                   'urgency': 'emergency',
                   'reported_location': 'Kileleshwa, Mandera Road, House 23 - front yard',
                   'status': 'resolved',
                   'related_asset': assets[2] if len(assets) > 2 else None,
                   'days_ago': 12
               },
               {
                   'customer': customers[4],
                   'issue_type': 'water_quality',
                   'title': 'Water quality issues - brown colored water',
                   'description': 'The water coming from our taps is brown in color and has a strange smell.',
                   'urgency': 'high',
                   'reported_location': 'Westlands, Chiromo Lane, Office Block 7 - all floors',
                   'status': 'acknowledged',
                   'days_ago': 1
               },
               {
                   'customer': customers[5],
                   'issue_type': 'billing_inquiry',
                   'title': 'High water bill inquiry',
                   'description': 'My water bill this month is unusually high compared to previous months. Please check for any issues.',
                   'urgency': 'low',
                   'reported_location': 'Lavington, Green Park Estate, House 18',
                   'status': 'open',
                   'days_ago': 3
               },
               {
                   'customer': customers[6],
                   'issue_type': 'connection_request',
                   'title': 'New connection for extension building',
                   'description': 'We need a new water connection for our extension building in the university campus.',
                   'urgency': 'standard',
                   'reported_location': 'University of Nairobi, Main Campus - new extension block',
                   'status': 'assigned',
                   'days_ago': 15
               },
               {
                   'customer': customers[7],
                   'issue_type': 'low_pressure',
                   'title': 'Low water pressure during peak hours',
                   'description': 'Water pressure drops significantly during morning and evening peak hours.',
                   'urgency': 'standard',
                   'reported_location': 'Kilimani, Ralph Bunche Road, Apartment 4B',
                   'status': 'open',
                   'days_ago': 1
               }
           ]
           
           service_requests = []
           for req_data in service_requests_data:
               days_ago = req_data.pop('days_ago', 1)
               created_date = timezone.now() - timedelta(days=days_ago)
               
               # Assign staff member if status requires it
               if req_data['status'] in ['assigned', 'in_progress', 'resolved']:
                   req_data['assigned_to'] = random.choice(all_staff) if all_staff else None
                   req_data['assigned_at'] = created_date + timedelta(hours=random.randint(1, 6))
               
               if req_data['status'] in ['acknowledged', 'assigned', 'in_progress', 'resolved']:
                   req_data['acknowledged_at'] = created_date + timedelta(minutes=random.randint(30, 180))
               
               if req_data['status'] == 'resolved':
                   req_data['resolved_at'] = created_date + timedelta(days=random.randint(1, 5))
                   req_data['resolution_notes'] = 'Issue has been resolved successfully.'
                   req_data['resolution_category'] = 'resolved_field'
                   req_data['customer_rating'] = random.randint(4, 5)
                   req_data['customer_feedback'] = 'Great service, thank you!'
               
               # Create location coordinates (Nairobi area)
               req_data['location_coordinates'] = Point(
                   36.8 + random.uniform(-0.1, 0.1),  # Longitude
                   -1.3 + random.uniform(-0.1, 0.1),  # Latitude
                   srid=4326
               )
               
               service_request = ServiceRequest.objects.create(**req_data)
               
               # Manually set creation date
               service_request.created_at = created_date
               service_request.save()
               
               service_requests.append(service_request)
               self.stats['service_requests'] += 1
           
           # Add comments to some service requests
           comment_templates = [
               "Thank you for reporting this issue. We have received your request and will assign a technician soon.",
               "Our technician is on the way to investigate the issue.",
               "The issue has been identified and repair work is in progress.",
               "We have completed the repair work. Please check if the issue is resolved.",
               "Thank you for your patience. The issue should now be resolved.",
               "Please let us know if you experience any further issues.",
               "We have tested the system and everything appears to be working normally.",
               "A follow-up inspection has been scheduled to ensure the repair is holding."
           ]
           
           customer_comments = [
               "Thank you for the quick response!",
               "The issue is now resolved, great work!",
               "Still experiencing some problems, please check again.",
               "Everything is working perfectly now.",
               "Very satisfied with the service quality.",
               "Could you please provide an update on the progress?"
           ]
           
           comments_created = 0
           for service_request in service_requests[:6]:  # Add comments to first 6 requests
               # Staff comments
               for i in range(random.randint(1, 3)):
                   staff_member = service_request.assigned_to or random.choice(support_users) if support_users else None
                   if staff_member:
                       comment_date = service_request.created_at + timedelta(
                           days=random.randint(0, 3),
                           hours=random.randint(1, 8)
                       )
                       
                       ServiceRequestComment.objects.create(
                           service_request=service_request,
                           author_staff=staff_member,
                           comment=random.choice(comment_templates),
                           is_internal=False,
                           created_at=comment_date
                       )
                       comments_created += 1
               
               # Customer response comments
               if random.choice([True, False]):
                   customer_comment_date = service_request.created_at + timedelta(
                       days=random.randint(1, 4),
                       hours=random.randint(2, 10)
                   )
                   
                   ServiceRequestComment.objects.create(
                       service_request=service_request,
                       author_customer=service_request.customer,
                       comment=random.choice(customer_comments),
                       is_internal=False,
                       created_at=customer_comment_date
                   )
                   comments_created += 1
           
           self.stats['comments'] = comments_created
           print_success(f"Created {self.stats['service_requests']} service requests and {comments_created} comments")
   
   def run_seeding(self):
       print(f"\n{Colors.BOLD}🚀 AccessWash Platform Complete Data Seeding{Colors.ENDC}")
       print("=" * 60)
       
       try:
           self.check_hosts_file()
           self.seed_tenants()
           self.seed_users() 
           self.seed_core_data()
           self.seed_infrastructure()
           self.seed_operational_data()
           
           # NEW: Customer portal data
           customers = self.seed_customer_data()
           self.seed_service_requests(customers)
           
           print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 Complete Seeding Finished!{Colors.ENDC}")
           print("\n📊 Final Database Contents:")
           print("=" * 40)
           print(f"🏢 Tenants: {self.stats['tenants']}")
           print(f"👥 Staff Users: {self.stats['users']}")
           print(f"🗺️  Zones: {self.stats['zones']}")
           print(f"🏗️  Assets: {self.stats['assets']}")
           print(f"🔍 Inspections: {self.stats['inspections']}")
           print(f"👨‍👩‍👧‍👦 Customers: {self.stats['customers']}")
           print(f"🎫 Service Requests: {self.stats['service_requests']}")
           print(f"💬 Comments: {self.stats['comments']}")
           print("=" * 40)
           print(f"📈 Total Records: {sum(self.stats.values())}")
           
           print(f"\n🌐 Access Points:")
           print(f"• Platform Admin: http://localhost:8000/admin/")
           print(f"• Demo Utility Admin: http://{CONFIG['DEMO_DOMAIN']}:8000/admin/")
           print(f"• API Documentation: http://{CONFIG['DEMO_DOMAIN']}:8000/api/docs/")
           print(f"• Customer Portal API: http://{CONFIG['DEMO_DOMAIN']}:8000/api/portal/")
           print(f"• Support API: http://{CONFIG['DEMO_DOMAIN']}:8000/api/support/")
           
           print(f"\n👤 Login Credentials (All users password: {CONFIG['PASSWORD']}):")
           print("🏢 STAFF USERS:")
           print(f"• Platform Admin: {CONFIG['ADMIN_EMAIL']}")
           print(f"• Demo Manager: manager@nairobidemo.accesswash.org")
           print(f"• Supervisor: supervisor@nairobidemo.accesswash.org")
           print(f"• Field Tech: field1@nairobidemo.accesswash.org")
           print(f"• Customer Support: support1@nairobidemo.accesswash.org")
           
           print("\n👨‍👩‍👧‍👦 CUSTOMER USERS:")
           print("• john.doe@example.com (Residential)")
           print("• mary.wanjiku@example.com (Residential)")
           print("• peter.kamau@businesscorp.co.ke (Commercial)")
           print("• grace.njeri@gmail.com (Residential)")
           print("• david.ochieng@company.com (Commercial)")
           print("• jane.muthoni@email.com (Residential)")
           print("• samuel.kiprop@institution.org (Institutional)")
           print("• alice.waweru@home.com (Residential)")
           
           print(f"\n🚀 Next Steps:")
           print(f"1. Start server: python manage.py runserver")
           print(f"2. Visit Admin: http://{CONFIG['DEMO_DOMAIN']}:8000/admin/")
           print(f"3. Test Customer APIs: http://{CONFIG['DEMO_DOMAIN']}:8000/api/docs/")
           
           print(f"\n🧪 Test Customer Login:")
           print(f"POST http://{CONFIG['DEMO_DOMAIN']}:8000/api/portal/auth/login/")
           print('{"username": "john.doe@example.com", "password": "' + CONFIG['PASSWORD'] + '"}')           
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