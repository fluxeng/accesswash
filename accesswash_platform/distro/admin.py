from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from django.utils.html import format_html
from django.db import connection
from .models import (
    AssetType, Zone, Asset, Pipe, Valve, Meter,
    AssetPhoto, AssetInspection
)

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

# Apply the mixin to ALL distro admin classes
@admin.register(AssetType)
class AssetTypeAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'code', 'icon', 'color_preview', 'is_linear']
    list_filter = ['is_linear']
    search_fields = ['name', 'code']
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 30px; background-color: {}; '
            'border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'

@admin.register(Zone)
class ZoneAdmin(TenantOnlyAdminMixin, gis_admin.GISModelAdmin):
    list_display = ['name', 'code', 'population', 'households', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    default_zoom = 12
    map_width = 800
    map_height = 600

@admin.register(Asset)
class AssetAdmin(TenantOnlyAdminMixin, gis_admin.GISModelAdmin):
    list_display = [
        'asset_id', 'name', 'asset_type', 'zone', 'status',
        'condition_badge', 'last_inspection'
    ]
    list_filter = ['asset_type', 'status', 'condition', 'zone']
    search_fields = ['asset_id', 'name', 'address', 'tags']
    readonly_fields = ['asset_id', 'qr_code', 'created_by', 'created_at', 'updated_at']
    
    def condition_badge(self, obj):
        colors = {5: 'green', 4: 'blue', 3: 'orange', 2: 'red', 1: 'darkred'}
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.condition, 'gray'),
            obj.get_condition_display()
        )
    condition_badge.short_description = 'Condition'

@admin.register(Pipe)
class PipeAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['asset', 'diameter', 'material', 'length', 'pressure_rating']
    list_filter = ['material', 'diameter']
    search_fields = ['asset__asset_id', 'asset__name']

@admin.register(Valve)
class ValveAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['asset', 'valve_type', 'diameter', 'is_open', 'is_automated']
    list_filter = ['valve_type', 'is_open', 'is_automated']
    search_fields = ['asset__asset_id', 'asset__name']

@admin.register(Meter)
class MeterAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['serial_number', 'asset', 'meter_type', 'size', 'last_reading']
    list_filter = ['meter_type', 'size', 'brand']
    search_fields = ['serial_number', 'asset__asset_id']

@admin.register(AssetPhoto)
class AssetPhotoAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['asset', 'caption', 'taken_by', 'taken_at']
    list_filter = ['taken_at']
    search_fields = ['asset__asset_id', 'caption']

@admin.register(AssetInspection)
class AssetInspectionAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    list_display = [
        'asset', 'inspection_date', 'inspector', 'condition_rating',
        'requires_maintenance'
    ]
    list_filter = ['condition_rating', 'requires_maintenance', 'inspection_date']
    search_fields = ['asset__asset_id', 'asset__name', 'notes']