from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'core'
router = DefaultRouter()

urlpatterns = [
    # API URLs
    path('', include(router.urls)),
]

# Add admin views only if they exist
try:
    from . import admin_views
    urlpatterns += [
        # Admin email testing URLs
        path('admin/email-test/', admin_views.email_test_view, name='email_test'),
        path('admin/email-config/', admin_views.email_config_view, name='email_config'),
        path('admin/send-test-invitation/', admin_views.send_test_invitation, name='send_test_invitation'),
    ]
except ImportError:
    # admin_views not available, skip the admin URLs
    pass