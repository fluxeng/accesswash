#!/usr/bin/env python
"""
AccessWash Platform - Complete Tenant Diagnostic & Fix
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accesswash_platform.settings')
django.setup()

from django.db import connection
from django.core.management import call_command
from django_tenants.utils import schema_context, get_tenant_model, get_public_schema_name
from tenants.models import Utility, Domain

def deep_diagnostic():
    """Comprehensive tenant diagnostic"""
    print("🔍 DEEP TENANT DIAGNOSTIC")
    print("=" * 60)
    
    # 1. Check django-tenants configuration
    print("1. DJANGO-TENANTS CONFIGURATION:")
    from django.conf import settings
    
    print(f"   TENANT_MODEL: {getattr(settings, 'TENANT_MODEL', 'NOT SET')}")
    print(f"   TENANT_DOMAIN_MODEL: {getattr(settings, 'TENANT_DOMAIN_MODEL', 'NOT SET')}")
    print(f"   SHARED_APPS: {len(getattr(settings, 'SHARED_APPS', []))} apps")
    print(f"   TENANT_APPS: {len(getattr(settings, 'TENANT_APPS', []))} apps")
    
    # 2. Check middleware
    print("\n2. MIDDLEWARE CHECK:")
    middleware = getattr(settings, 'MIDDLEWARE', [])
    tenant_middleware = 'django_tenants.middleware.main.TenantMainMiddleware'
    
    if tenant_middleware in middleware:
        index = middleware.index(tenant_middleware)
        print(f"   TenantMainMiddleware position: {index} {'✅' if index == 0 else '❌'}")
    else:
        print(f"   TenantMainMiddleware: NOT FOUND ❌")
    
    # 3. Check current connection
    print(f"\n3. CURRENT CONNECTION:")
    print(f"   Schema: {connection.schema_name}")
    print(f"   Database: {connection.settings_dict['NAME']}")
    
    # 4. Check database schemas
    print(f"\n4. DATABASE SCHEMAS:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;")
        schemas = [row[0] for row in cursor.fetchall()]
        print(f"   Available schemas: {schemas}")
        
        # Check if demo schema has tables
        if 'demo' in schemas:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'demo' AND table_name LIKE '%asset%'
                ORDER BY table_name;
            """)
            demo_tables = [row[0] for row in cursor.fetchall()]
            print(f"   Demo schema asset tables: {demo_tables}")
        else:
            print(f"   Demo schema: NOT FOUND ❌")
    
    # 5. Check tenant records
    print(f"\n5. TENANT RECORDS:")
    try:
        utilities = Utility.objects.all()
        print(f"   Total utilities: {utilities.count()}")
        for utility in utilities:
            print(f"   - {utility.name} (schema: {utility.schema_name}, active: {utility.is_active})")
        
        domains = Domain.objects.all()
        print(f"   Total domains: {domains.count()}")
        for domain in domains:
            print(f"   - {domain.domain} -> {domain.tenant.schema_name} (primary: {domain.is_primary})")
    except Exception as e:
        print(f"   Error accessing tenant records: {e}")
    
    # 6. Test schema switching
    print(f"\n6. SCHEMA SWITCHING TEST:")
    try:
        # Test public schema
        with schema_context('public'):
            print(f"   Public schema access: ✅")
            
        # Test demo schema
        if 'demo' in schemas:
            with schema_context('demo'):
                print(f"   Demo schema access: ✅")
                
                # Try importing distro models
                try:
                    from distro.models import AssetType
                    count = AssetType.objects.count()
                    print(f"   AssetType model access: ✅ ({count} records)")
                except Exception as e:
                    print(f"   AssetType model access: ❌ ({e})")
        else:
            print(f"   Demo schema: NOT AVAILABLE ❌")
            
    except Exception as e:
        print(f"   Schema switching error: {e}")
    
    # 7. Check tenant routing
    print(f"\n7. TENANT ROUTING TEST:")
    try:
        from django_tenants.utils import get_tenant_domain_model
        DomainModel = get_tenant_domain_model()
        
        # Test localhost routing
        try:
            localhost_domain = DomainModel.objects.get(domain='localhost')
            print(f"   localhost -> {localhost_domain.tenant.schema_name} ✅")
        except DomainModel.DoesNotExist:
            print(f"   localhost domain: NOT FOUND ❌")
        
        # Test demo domain routing
        try:
            demo_domain = DomainModel.objects.get(domain='demo.accesswash.org')
            print(f"   demo.accesswash.org -> {demo_domain.tenant.schema_name} ✅")
        except DomainModel.DoesNotExist:
            print(f"   demo.accesswash.org domain: NOT FOUND ❌")
            
    except Exception as e:
        print(f"   Domain routing error: {e}")

def complete_fix():
    """Complete tenant setup fix"""
    print("\n🔧 COMPLETE TENANT FIX")
    print("=" * 60)
    
    try:
        # Step 1: Clean existing broken setup
        print("Step 1: Cleaning existing setup...")
        
        # Delete existing domains and tenants
        Domain.objects.all().delete()
        Utility.objects.all().delete()
        
        print("   Cleaned existing tenant records ✅")
        
        # Step 2: Create public tenant properly
        print("\nStep 2: Creating public tenant...")
        
        public_tenant = Utility.objects.create(
            schema_name='public',
            name='AccessWash Platform',
            is_active=True
        )
        
        Domain.objects.create(
            domain='localhost',
            tenant=public_tenant,
            is_primary=True,
            is_active=True
        )
        
        print("   Public tenant created ✅")
        
        # Step 3: Create demo tenant with schema
        print("\nStep 3: Creating demo tenant...")
        
        demo_tenant = Utility.objects.create(
            schema_name='demo',
            name='Nairobi Water & Sewerage Company',
            is_active=True
        )
        
        Domain.objects.create(
            domain='demo.accesswash.org',
            tenant=demo_tenant,
            is_primary=True,
            is_active=True
        )
        
        print("   Demo tenant created ✅")
        
        # Step 4: Create database schema
        print("\nStep 4: Creating database schema...")
        
        # Drop demo schema if exists
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS demo CASCADE;")
            print("   Dropped existing demo schema ✅")
        
        # Create fresh demo schema
        demo_tenant.create_schema(check_if_exists=False)
        print("   Created new demo schema ✅")
        
        # Step 5: Run migrations
        print("\nStep 5: Running migrations...")
        
        # First run shared migrations
        call_command('migrate_schemas', '--shared', verbosity=1)
        print("   Shared migrations completed ✅")
        
        # Then run tenant migrations
        call_command('migrate_schemas', '--schema=demo', verbosity=1)
        print("   Demo tenant migrations completed ✅")
        
        # Step 6: Verify setup
        print("\nStep 6: Verifying setup...")
        
        # Test demo schema access
        with schema_context('demo'):
            from distro.models import AssetType
            
            # Create a test asset type
            test_asset, created = AssetType.objects.get_or_create(
                code='test',
                defaults={
                    'name': 'Test Asset',
                    'icon': 'test-icon',
                    'color': '#000000',
                    'is_linear': False
                }
            )
            
            print(f"   Test asset type: {'created' if created else 'exists'} ✅")
            print(f"   Total asset types in demo: {AssetType.objects.count()}")
        
        print("\n🎉 TENANT SETUP COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"\n❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_data():
    """Create minimal sample data for testing"""
    print("\n📊 CREATING SAMPLE DATA")
    print("=" * 60)
    
    try:
        with schema_context('demo'):
            from distro.models import AssetType, Zone
            from django.contrib.gis.geos import Polygon
            
            # Create asset types
            asset_types = [
                {'name': 'Water Pipe', 'code': 'pipe', 'icon': 'pipe', 'color': '#2563EB', 'is_linear': True},
                {'name': 'Valve', 'code': 'valve', 'icon': 'valve', 'color': '#DC2626', 'is_linear': False},
                {'name': 'Water Meter', 'code': 'meter', 'icon': 'meter', 'color': '#059669', 'is_linear': False},
            ]
            
            created_types = 0
            for at_data in asset_types:
                asset_type, created = AssetType.objects.get_or_create(
                    code=at_data['code'], defaults=at_data
                )
                if created:
                    created_types += 1
            
            print(f"   Created {created_types} asset types ✅")
            
            # Create a test zone
            zone, created = Zone.objects.get_or_create(
                code='TEST001',
                defaults={
                    'name': 'Test Zone',
                    'boundary': Polygon([
                        [36.79, -1.27], [36.82, -1.27], 
                        [36.82, -1.24], [36.79, -1.24], [36.79, -1.27]
                    ]),
                    'population': 10000,
                    'households': 2500
                }
            )
            
            print(f"   Test zone: {'created' if created else 'exists'} ✅")
            
            print(f"\n   Total AssetTypes: {AssetType.objects.count()}")
            print(f"   Total Zones: {Zone.objects.count()}")
        
        return True
        
    except Exception as e:
        print(f"   Sample data creation failed: {e}")
        return False

def final_verification():
    """Final verification of tenant setup"""
    print("\n✅ FINAL VERIFICATION")
    print("=" * 60)
    
    # Check schemas in database
    with connection.cursor() as cursor:
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('public', 'demo');")
        schemas = [row[0] for row in cursor.fetchall()]
        print(f"Database schemas: {schemas}")
    
    # Check tenant records
    utilities = Utility.objects.all()
    domains = Domain.objects.all()
    
    print(f"Tenant records:")
    for utility in utilities:
        print(f"  - {utility.name} ({utility.schema_name})")
    
    print(f"Domain records:")
    for domain in domains:
        print(f"  - {domain.domain} -> {domain.tenant.schema_name}")
    
    # Test demo schema access
    try:
        with schema_context('demo'):
            from distro.models import AssetType
            count = AssetType.objects.count()
            print(f"Demo schema test: ✅ ({count} asset types)")
    except Exception as e:
        print(f"Demo schema test: ❌ ({e})")
    
    print(f"\n🚀 NEXT STEPS:")
    print(f"1. Ensure hosts file: echo '127.0.0.1 demo.accesswash.org' | sudo tee -a /etc/hosts")
    print(f"2. Start server: python manage.py runserver")
    print(f"3. Visit: http://demo.accesswash.org:8000/admin/")
    print(f"4. You should see 'Distro Field Operations' section")

if __name__ == "__main__":
    # Run full diagnostic
    deep_diagnostic()
    
    # Ask for fix
    if input("\nRun complete fix? This will recreate tenant setup (y/n): ").lower().startswith('y'):
        if complete_fix():
            if input("\nCreate sample data for testing? (y/n): ").lower().startswith('y'):
                create_sample_data()
            final_verification()
        else:
            print("❌ Fix failed. Check the errors above.")
    
    print(f"\n" + "="*60)
    print(f"Diagnostic complete. Check output above for issues.")