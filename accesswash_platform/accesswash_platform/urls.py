"""
URLs for AccessWash Platform - PROPERLY FIXED VERSION
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import redirect
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
)

def schema_health_check(request):
    """Health check that shows current schema"""
    from django.db import connection
    schema = getattr(connection, 'schema_name', 'unknown')
    tenant_info = getattr(connection, 'tenant', None)
    tenant_name = tenant_info.name if tenant_info else 'Unknown'
    
    return HttpResponse(f'AccessWash OK - Schema: {schema} - Tenant: {tenant_name}')

def schema_aware_redirect(request):
    """Redirect based on current schema"""
    from django.db import connection
    schema = getattr(connection, 'schema_name', 'public')
    
    if schema == 'public':
        return redirect('/admin/')  # Go to tenant management
    else:
        return redirect('/api/docs/')  # Go to API docs for tenant

# ALL URLs - Let django-tenants handle the routing
urlpatterns = [
    # Admin interface - available everywhere
    path('admin/', admin.site.urls),
    
    # API Documentation - available everywhere  
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health check with schema info
    path('health/', schema_health_check, name='health'),
    
    # DRF browsable API
    path('api-auth/', include('rest_framework.urls')),
    
    # ALL API endpoints - django-tenants will filter what's available
    path('api/tenants/', include('tenants.urls')),      # Only works in public schema
    path('api/users/', include('users.urls')),          # Works in both schemas
    path('api/core/', include('core.urls')),            # Only works in tenant schemas
    path('api/distro/', include('distro.urls')),        # Only works in tenant schemas
    
    # Smart redirect based on schema
    path('', schema_aware_redirect, name='home'),
]

# Static files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site configuration
admin.site.site_header = "AccessWASH Platform V 1.00"
admin.site.site_title = "AccessWASH Admin"
admin.site.index_title = "Water Utility Management"