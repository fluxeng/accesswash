"""
URLs for AccessWash Platform - FIXED VERSION
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
from django.db import connection

def schema_health_check(request):
    """Health check that shows current schema"""
    schema = getattr(connection, 'schema_name', 'unknown')
    return HttpResponse(f'AccessWash OK - Schema: {schema}')

# Base URL patterns for all schemas
urlpatterns = [
    # Admin interface - available everywhere
    path('admin/', admin.site.urls),
    
    # API Documentation - available everywhere  
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Users API - available everywhere
    path('api/users/', include('users.urls')),
    
    # Health check with schema info
    path('health/', schema_health_check, name='health'),
    
    # DRF browsable API
    path('api-auth/', include('rest_framework.urls')),
]

# Add schema-specific URLs
try:
    current_schema = getattr(connection, 'schema_name', 'public')
    
    if current_schema == 'public':
        # Public schema: tenant management only
        urlpatterns.extend([
            path('api/tenants/', include('tenants.urls')),
            path('', lambda request: redirect('/api/docs/')),
        ])
    else:
        # Tenant schemas: operational apps
        urlpatterns.extend([
            path('api/core/', include('core.urls')),
            path('api/distro/', include('distro.urls')),  # THIS WILL NOW WORK!
            path('', lambda request: redirect('/api/docs/')),
        ])
        
except Exception:
    # Fallback - include all URLs if schema detection fails
    urlpatterns.extend([
        path('api/tenants/', include('tenants.urls')),
        path('api/core/', include('core.urls')), 
        path('api/distro/', include('distro.urls')),
        path('', lambda request: redirect('/api/docs/')),
    ])

# Static files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site configuration
admin.site.site_header = "AccessWash Platform V 1.00"
admin.site.site_title = "AccessWash Admin"
admin.site.index_title = "Water Utility Management"