"""
accesswash_platform/accesswash_platform/urls.py
Simplified URLs configuration for AccessWash Platform
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
import datetime


def health_check(request):
    """Enhanced health check with service status"""
    from django.db import connection
    from django.core.cache import cache
    
    try:
        # Get tenant info
        schema = getattr(connection, 'schema_name', 'public')
        tenant = getattr(connection, 'tenant', None)
        tenant_name = getattr(tenant, 'name', 'Platform') if tenant else 'Platform'
        
        # Service checks
        services = {}
        
        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            services['database'] = 'OK'
        except Exception:
            services['database'] = 'ERROR'
        
        # Cache check
        try:
            test_key = 'health_test'
            cache.set(test_key, 'test', 10)
            cache_result = cache.get(test_key)
            services['cache'] = 'OK' if cache_result == 'test' else 'ERROR'
            cache.delete(test_key)
        except Exception:
            services['cache'] = 'ERROR'
        
        # Email backend check
        try:
            from django.core.mail import get_connection
            get_connection()
            services['email'] = 'OK'
        except Exception:
            services['email'] = 'ERROR'
        
        # Overall status
        all_ok = all(status == 'OK' for status in services.values())
        overall_status = 'healthy' if all_ok else 'degraded'
        
        health_data = {
            'status': overall_status,
            'timestamp': datetime.datetime.now().isoformat(),
            'tenant': tenant_name,
            'schema': schema,
            'services': services
        }
        
        # Return JSON or HTML
        if 'application/json' in request.headers.get('Accept', '') or request.GET.get('format') == 'json':
            return JsonResponse(health_data)
        
        status_emoji = '✅' if overall_status == 'healthy' else '⚠️'
        services_html = '<br>'.join([f"{service}: {status}" for service, status in services.items()])
        
        return HttpResponse(f"""
        <h1>🌊 AccessWash Health Check</h1>
        <p>Status: {status_emoji} <strong>{overall_status.upper()}</strong></p>
        <p>Tenant: {tenant_name} ({schema})</p>
        <p>Services:<br>{services_html}</p>
        <p><a href="/admin/">Admin</a> | <a href="/api/docs/">API Docs</a> | <a href="/health/?format=json">JSON</a></p>
        <small>Last check: {health_data['timestamp']}</small>
        """)
        
    except Exception as e:
        error_data = {'status': 'unhealthy', 'error': str(e), 'timestamp': datetime.datetime.now().isoformat()}
        if 'application/json' in request.headers.get('Accept', '') or request.GET.get('format') == 'json':
            return JsonResponse(error_data, status=503)
        return HttpResponse(f"<h1>❌ Health Check Failed</h1><p>{e}</p>", status=503)


def home_redirect(request):
    """Redirect to appropriate interface based on schema"""
    from django.db import connection
    schema = getattr(connection, 'schema_name', 'public')
    return redirect('/admin/' if schema == 'public' else '/api/docs/')


def ping(request):
    """Simple ping for load balancers"""
    return HttpResponse("OK")


# URL Configuration
urlpatterns = [
    # Health & Monitoring
    path('health/', health_check, name='health'),
    path('ping/', ping, name='ping'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation  
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication
    path('api-auth/', include('rest_framework.urls')),
    
    # API Endpoints
    path('api/tenants/', include('tenants.urls')),      # Platform only
    path('api/users/', include('users.urls')),          # Both schemas  
    path('api/core/', include('core.urls')),            # Tenants only
    path('api/distro/', include('distro.urls')),        # Tenants only
    path('api/portal/', include('portal.urls')),        # Customer portal
    path('api/support/', include('support.urls')),      # Support
    
    # Home redirect
    path('', home_redirect, name='home'),
]

# Static files (development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin configuration
admin.site.site_header = "AccessWASH Platform"
admin.site.site_title = "AccessWASH Admin"  
admin.site.index_title = "Water Utility Management"