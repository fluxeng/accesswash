"""
URLs for AccessWash Platform
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

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # APIs - work in appropriate schemas
    path('api/tenants/', include('tenants.urls')),      # Public schema only
    path('api/users/', include('users.urls')),          # Both schemas
    path('api/core/', include('core.urls')),            # Both schemas
    path('api/distro/', include('distro.urls')),        # Tenant schemas only
    
    # DRF Auth
    path('api-auth/', include('rest_framework.urls')),
    
   
    # Health check
    path('health/', lambda request: HttpResponse('AccessWash OK')),
    
    # Root redirect
    path('', lambda request: redirect('/api/docs/')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin configuration
admin.site.site_header = "AccessWash Platform V 1.00"
admin.site.site_title = "AccessWash Admin"
admin.site.index_title = "Water Utility Management"