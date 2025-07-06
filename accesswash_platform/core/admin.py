from django.contrib import admin
from django.utils.html import format_html
from django.db import connection
from django.shortcuts import redirect
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from .models import UtilitySettings


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


@admin.register(UtilitySettings)
class UtilitySettingsAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """Simple admin that automatically manages utility settings"""
    
    # Show key fields in list view
    list_display = [
        'utility_name', 'contact_info', 'logo_preview', 
        'color_preview', 'enabled_modules', 'updated_at'
    ]
    
    # No filters needed - there's only one object per tenant
    list_filter = []
    
    # Search is not needed for single object
    search_fields = []
    
    # Make timestamps readonly
    readonly_fields = ['created_at', 'updated_at', 'color_preview_detail']
    
    # Organize fields logically
    fieldsets = (
        ('Utility Information', {
            'fields': ('utility_name', 'logo', 'address'),
            'description': 'Basic information about your water utility'
        }),
        ('Contact Details', {
            'fields': ('contact_phone', 'contact_email', 'website'),
            'description': 'How customers can reach you'
        }),
        ('Branding', {
            'fields': ('primary_color', 'secondary_color', 'color_preview_detail'),
            'description': 'Colors for your utility interface'
        }),
        ('Available Modules', {
            'fields': (
                'distro_enabled', 'huduma_enabled', 'maji_enabled', 
                'hesabu_enabled', 'ripoti_enabled'
            ),
            'description': 'Enable the modules you want to use',
            'classes': ('wide',)
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_urls(self):
        """Add custom URL for auto-setup"""
        urls = super().get_urls()
        custom_urls = [
            path('auto-setup/', self.admin_site.admin_view(self.auto_setup_view), name='core_utilitysettings_auto_setup'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """Override to auto-redirect to the single object or create it"""
        # Check if settings exist
        settings = UtilitySettings.objects.first()
        
        if not settings:
            # Auto-create default settings
            settings = self.auto_create_settings()
        
        # Redirect directly to the edit page
        return HttpResponseRedirect(
            reverse('admin:core_utilitysettings_change', args=[settings.pk])
        )
    
    def auto_create_settings(self):
        """Automatically create default utility settings"""
        from django.db import connection
        
        # Get tenant info
        tenant = getattr(connection, 'tenant', None)
        utility_name = tenant.name if tenant else 'Water Utility'
        
        # Create with sensible defaults
        settings = UtilitySettings.objects.create(
            utility_name=utility_name,
            primary_color='#2563eb',  # Nice blue
            secondary_color='#1e40af',  # Darker blue
            distro_enabled=True,  # Enable the main module by default
            huduma_enabled=False,
            maji_enabled=False,
            hesabu_enabled=False,
            ripoti_enabled=False,
        )
        
        return settings
    
    def auto_setup_view(self, request):
        """Auto-setup endpoint (not needed with auto-creation)"""
        settings = UtilitySettings.objects.first()
        if not settings:
            settings = self.auto_create_settings()
        
        return HttpResponseRedirect(
            reverse('admin:core_utilitysettings_change', args=[settings.pk])
        )
    
    def contact_info(self, obj):
        """Display contact information"""
        info = []
        if obj.contact_phone:
            info.append(f"📞 {obj.contact_phone}")
        if obj.contact_email:
            info.append(f"✉️ {obj.contact_email}")
        
        return format_html('<br>'.join(info)) if info else '—'
    contact_info.short_description = 'Contact'
    
    def logo_preview(self, obj):
        """Small logo preview"""
        if obj.logo:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" />',
                obj.logo.url
            )
        return '—'
    logo_preview.short_description = 'Logo'
    
    def color_preview(self, obj):
        """Color swatches preview"""
        return format_html(
            '<div style="display: flex; gap: 3px;">'
            '<div style="width: 18px; height: 18px; background-color: {}; border: 1px solid #ccc; border-radius: 2px;" title="{}"></div>'
            '<div style="width: 18px; height: 18px; background-color: {}; border: 1px solid #ccc; border-radius: 2px;" title="{}"></div>'
            '</div>',
            obj.primary_color, obj.primary_color,
            obj.secondary_color, obj.secondary_color
        )
    color_preview.short_description = 'Colors'
    
    def color_preview_detail(self, obj):
        """Detailed color preview for form"""
        return format_html(
            '<div style="margin: 10px 0; padding: 15px; background: #f8f9fa; border-radius: 5px;">'
            '<strong>Color Preview:</strong><br>'
            '<div style="display: flex; gap: 20px; margin-top: 10px;">'
            '<div style="text-align: center;">'
            '<div style="width: 60px; height: 40px; background-color: {}; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 5px;"></div>'
            '<small>Primary<br>{}</small>'
            '</div>'
            '<div style="text-align: center;">'
            '<div style="width: 60px; height: 40px; background-color: {}; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 5px;"></div>'
            '<small>Secondary<br>{}</small>'
            '</div>'
            '</div>'
            '</div>',
            obj.primary_color, obj.primary_color,
            obj.secondary_color, obj.secondary_color
        )
    color_preview_detail.short_description = 'Preview'
    
    def enabled_modules(self, obj):
        """Show enabled modules as colored badges"""
        modules = []
        
        if obj.distro_enabled:
            modules.append('<span style="background: #2563eb; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">Distro</span>')
        if obj.huduma_enabled:
            modules.append('<span style="background: #059669; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">Huduma</span>')
        if obj.maji_enabled:
            modules.append('<span style="background: #0891b2; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">Maji</span>')
        if obj.hesabu_enabled:
            modules.append('<span style="background: #7c3aed; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">Hesabu</span>')
        if obj.ripoti_enabled:
            modules.append('<span style="background: #dc2626; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">Ripoti</span>')
        
        if modules:
            return format_html(' '.join(modules))
        return format_html('<span style="color: #999;">None enabled</span>')
    enabled_modules.short_description = 'Modules'
    
    def has_add_permission(self, request):
        """Allow adding only if no settings exist"""
        return not UtilitySettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion"""
        return False
    
    def save_model(self, request, obj, form, change):
        """Ensure only one settings object exists per tenant"""
        if not change:  # New object
            # Delete any existing settings first
            UtilitySettings.objects.exclude(pk=obj.pk).delete()
        
        super().save_model(request, obj, form, change)
    
    def response_add(self, request, obj, post_url_continue=None):
        """Redirect to change view after adding"""
        return HttpResponseRedirect(
            reverse('admin:core_utilitysettings_change', args=[obj.pk])
        )
    
    def response_change(self, request, obj):
        """Stay on the same page after saving"""
        if '_save' in request.POST:
            return HttpResponseRedirect(
                reverse('admin:core_utilitysettings_change', args=[obj.pk])
            )
        return super().response_change(request, obj)


# Customize the admin site for better UX
class UtilityAdminSite(admin.AdminSite):
    """Custom admin site that shows utility info"""
    
    def index(self, request, extra_context=None):
        """Custom index with utility info"""
        extra_context = extra_context or {}
        
        # Get utility settings if they exist
        try:
            settings = UtilitySettings.objects.first()
            if settings:
                extra_context.update({
                    'utility_name': settings.utility_name,
                    'utility_colors': {
                        'primary': settings.primary_color,
                        'secondary': settings.secondary_color,
                    },
                    'has_utility_settings': True,
                })
        except:
            pass
        
        return super().index(request, extra_context)


# Override admin actions to remove bulk delete
def get_actions(self, request):
    """Remove delete action"""
    actions = super(UtilitySettingsAdmin, self).get_actions(request)
    if 'delete_selected' in actions:
        del actions['delete_selected']
    return actions

UtilitySettingsAdmin.get_actions = get_actions