from django.contrib import admin
from django.utils.html import format_html
from django.db import connection
from django.urls import reverse
from .models import Customer, CustomerSession, CustomerVerification


def is_tenant_schema():
    """Check if we're in a tenant schema (not public)"""
    try:
        schema = getattr(connection, 'schema_name', 'public')
        return schema != 'public'
    except:
        return False


class TenantOnlyAdminMixin:
    """Only show in tenant schemas, not public schema"""
    
    def has_module_permission(self, request):
        return is_tenant_schema() and super().has_module_permission(request)


@admin.register(Customer)
class CustomerAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for customers"""
    
    list_display = [
        'email', 'get_full_name', 'account_number', 'service_type',
        'email_verified', 'phone_verified', 'is_active', 'created_at'
    ]
    list_filter = [
        'service_type', 'email_verified', 'phone_verified', 
        'is_active', 'is_deleted', 'created_at', 'language'
    ]
    search_fields = [
        'email', 'first_name', 'last_name', 'account_number', 
        'meter_number', 'property_address'
    ]
    readonly_fields = [
        'id', 'password_hash', 'last_login', 'last_activity',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'phone_number', 'first_name', 'last_name')
        }),
        ('Account Details', {
            'fields': ('account_number', 'meter_number', 'meter', 'service_type')
        }),
        ('Address & Location', {
            'fields': ('property_address', 'property_location', 'connection_date')
        }),
        ('Preferences', {
            'fields': ('language', 'notification_preferences')
        }),
        ('Status', {
            'fields': ('is_active', 'email_verified', 'phone_verified', 'is_deleted')
        }),
        ('Activity', {
            'fields': ('last_login', 'last_activity', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Name'
    
    def get_queryset(self, request):
        """Include deleted customers if requested"""
        qs = super().get_queryset(request)
        if request.GET.get('show_deleted'):
            return qs
        return qs.filter(is_deleted=False)
    
    actions = ['verify_email', 'verify_phone', 'activate_customers', 'deactivate_customers']
    
    def verify_email(self, request, queryset):
        count = queryset.update(email_verified=True)
        self.message_user(request, f'{count} customers email verified.')
    
    def verify_phone(self, request, queryset):
        count = queryset.update(phone_verified=True)
        self.message_user(request, f'{count} customers phone verified.')
    
    def activate_customers(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} customers activated.')
    
    def deactivate_customers(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} customers deactivated.')


@admin.register(CustomerSession)
class CustomerSessionAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for customer sessions"""
    
    list_display = [
        'customer', 'ip_address', 'is_active', 'expires_at', 
        'created_at', 'last_used_at'
    ]
    list_filter = ['is_active', 'created_at', 'expires_at']
    search_fields = ['customer__email', 'ip_address']
    readonly_fields = ['session_token', 'refresh_token', 'created_at', 'last_used_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer')


@admin.register(CustomerVerification)
class CustomerVerificationAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for customer verifications"""
    
    list_display = [
        'customer', 'verification_type', 'email', 'phone_number',
        'is_used', 'expires_at', 'created_at'
    ]
    list_filter = ['verification_type', 'is_used', 'created_at', 'expires_at']
    search_fields = ['customer__email', 'email', 'phone_number']
    readonly_fields = ['token', 'created_at', 'used_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer')