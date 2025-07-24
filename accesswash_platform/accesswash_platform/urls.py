"""
File: accesswash_platform/accesswash_platform/urls.py
Complete fixed URLs for AccessWash Platform with better health checks
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
)
import json

def enhanced_health_check(request):
    """Enhanced health check with tenant and service information"""
    from django.db import connection
    from django.core.cache import cache
    import datetime
    
    try:
        # Get tenant info
        schema = getattr(connection, 'schema_name', 'unknown')
        tenant_info = getattr(connection, 'tenant', None)
        tenant_name = getattr(tenant_info, 'name', 'Unknown') if tenant_info else 'Platform'
        
        # Test database
        try:
            from django.db import connections
            db_conn = connections['default']
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_status = "OK"
        except Exception as e:
            db_status = f"ERROR: {e}"
        
        # Test cache
        try:
            test_key = "health_check_test"
            cache.set(test_key, "test", 30)
            cache_value = cache.get(test_key)
            cache_status = "OK" if cache_value == "test" else "ERROR"
            cache.delete(test_key)
        except Exception as e:
            cache_status = f"ERROR: {e}"
        
        # Test email backend
        try:
            from django.core.mail import get_connection
            email_connection = get_connection()
            email_status = f"OK ({settings.EMAIL_BACKEND})"
        except Exception as e:
            email_status = f"ERROR: {e}"
        
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'tenant': {
                'schema': schema,
                'name': tenant_name,
                'is_public': schema == 'public'
            },
            'services': {
                'database': db_status,
                'cache': cache_status,
                'email': email_status
            },
            'version': '1.0.0'
        }
        
        # Return JSON for API calls, HTML for browser
        if request.headers.get('Accept', '').startswith('application/json'):
            return JsonResponse(health_data)
        else:
            return HttpResponse(f'''
            <!DOCTYPE html>
            <html>
            <head><title>AccessWash Health Check</title></head>
            <body style="font-family: Arial, sans-serif; margin: 40px;">
                <h1>🌊 AccessWash Platform Health Check</h1>
                <h2>✅ System Status: {health_data['status'].upper()}</h2>
                
                <h3>🏢 Tenant Information</h3>
                <ul>
                    <li><strong>Schema:</strong> {schema}</li>
                    <li><strong>Name:</strong> {tenant_name}</li>
                    <li><strong>Type:</strong> {"Platform" if schema == "public" else "Utility"}</li>
                </ul>
                
                <h3>🔧 Service Status</h3>
                <ul>
                    <li><strong>Database:</strong> {db_status}</li>
                    <li><strong>Cache:</strong> {cache_status}</li>
                    <li><strong>Email:</strong> {email_status}</li>
                </ul>
                
                <h3>🔗 Quick Links</h3>
                <ul>
                    <li><a href="/admin/">Admin Interface</a></li>
                    <li><a href="/api/docs/">API Documentation</a></li>
                    <li><a href="/api/schema/">API Schema</a></li>
                </ul>
                
                <p><small>Timestamp: {health_data['timestamp']}</small></p>
            </body>
            </html>
            ''', content_type='text/html')
            
    except Exception as e:
        error_data = {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        if request.headers.get('Accept', '').startswith('application/json'):
            return JsonResponse(error_data, status=503)
        else:
            return HttpResponse(f'''
            <!DOCTYPE html>
            <html>
            <head><title>AccessWash Health Check - Error</title></head>
            <body style="font-family: Arial, sans-serif; margin: 40px;">
                <h1>❌ AccessWash Platform Health Check</h1>
                <h2>🚨 System Status: UNHEALTHY</h2>
                <p><strong>Error:</strong> {error_data['error']}</p>
                <p><small>Timestamp: {error_data['timestamp']}</small></p>
            </body>
            </html>
            ''', content_type='text/html', status=503)

def schema_aware_redirect(request):
    """Smart redirect based on current schema"""
    from django.db import connection
    schema = getattr(connection, 'schema_name', 'public')
    
    if schema == 'public':
        return redirect('/admin/')  # Platform management
    else:
        return redirect('/api/docs/')  # Tenant API docs

def simple_health(request):
    """Simple health check for load balancers"""
    return HttpResponse("OK", content_type='text/plain')

# Main URL patterns - django-tenants handles routing
urlpatterns = [
    # Health checks (highest priority)
    path('health/', enhanced_health_check, name='health'),
    path('ping/', simple_health, name='ping'),
    
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication (DRF)
    path('api-auth/', include('rest_framework.urls')),
    
    # API endpoints - django-tenants filters availability
    path('api/tenants/', include('tenants.urls')),      # Public schema only
    path('api/users/', include('users.urls')),          # Both schemas
    path('api/core/', include('core.urls')),            # Tenant schemas only  
    path('api/distro/', include('distro.urls')),        # Tenant schemas only
    
    # Smart home redirect
    path('', schema_aware_redirect, name='home'),
]

# Static and media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site configuration
admin.site.site_header = "AccessWASH Platform V 1.00"
admin.site.site_title = "AccessWASH Admin"  
admin.site.index_title = "Water Utility Management"