from django.contrib import admin
from django.db import connection
from django_tenants.admin import TenantAdminMixin
from django_tenants.utils import get_public_schema_name

from .models import Utility, Domain


def is_public_schema():
    """Check if we're currently in the public schema"""
    try:
        current_schema = connection.schema_name
        public_schema = get_public_schema_name()
        return current_schema == public_schema
    except:
        return connection.schema_name in ['public', None]


@admin.register(Utility)
class UtilityAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'is_active', 'created_on')
    list_filter = ('is_active', 'created_on')
    search_fields = ('name', 'schema_name')
    readonly_fields = ('created_on',)
    
    def has_module_permission(self, request):
        return is_public_schema() and super().has_module_permission(request)
    
    def has_view_permission(self, request, obj=None):
        return is_public_schema() and super().has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        return is_public_schema() and super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        return is_public_schema() and super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        return is_public_schema() and super().has_delete_permission(request, obj)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'schema_name')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_on',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Domain)
class DomainAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary', 'is_active')
    list_filter = ('is_primary', 'is_active')
    search_fields = ('domain', 'tenant__name')
    
    def has_module_permission(self, request):
        return is_public_schema() and super().has_module_permission(request)
    
    def has_view_permission(self, request, obj=None):
        return is_public_schema() and super().has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        return is_public_schema() and super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        return is_public_schema() and super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        return is_public_schema() and super().has_delete_permission(request, obj)
    
    fieldsets = (
        ('Domain Information', {
            'fields': ('domain', 'tenant', 'is_primary')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('tenant')


# Force unregister from tenant schemas
if not is_public_schema():
    try:
        admin.site.unregister(Utility)
        admin.site.unregister(Domain)
    except admin.sites.NotRegistered:
        pass