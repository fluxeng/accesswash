#!/usr/bin/env python
"""
Script to properly set up domains for AccessWash Platform
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accesswash_platform.settings')
django.setup()

from tenants.models import Utility, Domain
from django.db import transaction

def setup_domains():
    """Set up all required domains"""
    
    print("🌐 Setting up AccessWash domains...")
    
    with transaction.atomic():
        # 1. Get or create public tenant
        public_tenant, created = Utility.objects.get_or_create(
            schema_name='public',
            defaults={
                'name': 'AccessWash Platform',
                'is_active': True
            }
        )
        if created:
            print("✅ Created public tenant")
        else:
            print("✅ Public tenant exists")
        
        # 2. Create domains for public tenant
        public_domains = [
            'localhost',
            'api.accesswash.org',
            '127.0.0.1',
        ]
        
        for domain_name in public_domains:
            domain, created = Domain.objects.get_or_create(
                domain=domain_name,
                defaults={
                    'tenant': public_tenant,
                    'is_primary': domain_name == 'localhost',
                    'is_active': True
                }
            )
            if created:
                print(f"✅ Created domain: {domain_name}")
            else:
                print(f"✅ Domain exists: {domain_name}")
        
        # 3. Get or create demo tenant
        demo_tenant, created = Utility.objects.get_or_create(
            schema_name='demo',
            defaults={
                'name': 'Nairobi Water & Sewerage Company',
                'is_active': True
            }
        )
        if created:
            print("✅ Created demo tenant")
            # Create schema if new
            demo_tenant.create_schema(check_if_exists=True)
            print("✅ Created demo schema")
        else:
            print("✅ Demo tenant exists")
        
        # 4. Create domains for demo tenant
        demo_domains = [
            'demo.accesswash.org',
            'demo.localhost',
        ]
        
        for domain_name in demo_domains:
            domain, created = Domain.objects.get_or_create(
                domain=domain_name,
                defaults={
                    'tenant': demo_tenant,
                    'is_primary': domain_name == 'demo.accesswash.org',
                    'is_active': True
                }
            )
            if created:
                print(f"✅ Created domain: {domain_name}")
            else:
                print(f"✅ Domain exists: {domain_name}")
    
    print("\n🎉 Domain setup complete!")
    print("\nDomains configured:")
    print("📋 Public Schema (Platform Management):")
    print("   - http://localhost:8000/admin/")
    print("   - http://api.accesswash.org:8000/admin/")
    print("   - http://127.0.0.1:8000/admin/")
    print("\n🏢 Demo Tenant (Water Utility Operations):")
    print("   - http://demo.accesswash.org:8000/admin/")
    print("   - http://demo.localhost:8000/admin/")
    print("   - http://demo.accesswash.org:8000/api/docs/")

if __name__ == "__main__":
    setup_domains()