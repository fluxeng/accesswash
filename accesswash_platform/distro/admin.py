from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from django.utils.html import format_html
from .models import (
    AssetType, Zone, Asset, Pipe, Valve, Meter,
    AssetPhoto, AssetInspection
)


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
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

from django.contrib.gis.admin import GISModelAdmin
@admin.register(Zone)
class ZoneAdmin(GISModelAdmin):
    list_display = ['name', 'code', 'population', 'households', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    
    # Map settings
    default_zoom = 12
    map_width = 800
    map_height = 600


class AssetPhotoInline(admin.TabularInline):
    model = AssetPhoto
    extra = 0
    readonly_fields = ['taken_by', 'taken_at']


class AssetInspectionInline(admin.TabularInline):
    model = AssetInspection
    extra = 0
    readonly_fields = ['inspector', 'inspection_date']
    fields = ['inspection_date', 'inspector', 'condition_rating', 'requires_maintenance']


from django.contrib.gis.admin import GISModelAdmin

@admin.register(Asset)
class AssetAdmin(GISModelAdmin):
    list_display = [
        'asset_id', 'name', 'asset_type', 'zone', 'status',
        'condition_badge', 'last_inspection'
    ]
    list_filter = ['asset_type', 'status', 'condition', 'zone']
    search_fields = ['asset_id', 'name', 'address', 'tags']
    readonly_fields = ['asset_id', 'qr_code', 'created_by', 'created_at', 'updated_at']
    
    inlines = [AssetPhotoInline, AssetInspectionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('asset_id', 'name', 'asset_type', 'qr_code')
        }),
        ('Location', {
            'fields': ('location', 'zone', 'address')
        }),
        ('Status', {
            'fields': ('status', 'condition', 'installation_date', 
                      'last_inspection', 'next_inspection')
        }),
        ('Details', {
            'fields': ('specifications', 'parent_asset', 'tags', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Map settings
    default_zoom = 16
    map_width = 800
    map_height = 600
    
    def condition_badge(self, obj):
        colors = {
            5: 'green',
            4: 'blue',
            3: 'orange',
            2: 'red',
            1: 'darkred'
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.condition, 'gray'),
            obj.get_condition_display()
        )
    condition_badge.short_description = 'Condition'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'asset_type', 'zone', 'created_by'
        )


@admin.register(Pipe)
class PipeAdmin(admin.ModelAdmin):
    list_display = ['asset', 'diameter', 'material', 'length', 'pressure_rating']
    list_filter = ['material', 'diameter']
    search_fields = ['asset__asset_id', 'asset__name']
    raw_id_fields = ['asset', 'start_node', 'end_node']


@admin.register(Valve)
class ValveAdmin(admin.ModelAdmin):
    list_display = [
        'asset', 'valve_type', 'diameter', 'is_open_display',
        'is_automated', 'last_operated'
    ]
    list_filter = ['valve_type', 'is_open', 'is_automated']
    search_fields = ['asset__asset_id', 'asset__name']
    raw_id_fields = ['asset']
    
    def is_open_display(self, obj):
        if obj.is_open:
            return format_html(
                '<span style="color: green;">● Open</span>'
            )
        return format_html(
            '<span style="color: red;">● Closed</span>'
        )
    is_open_display.short_description = 'Status'


@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    list_display = [
        'serial_number', 'asset', 'meter_type', 'size',
        'last_reading', 'last_reading_date'
    ]
    list_filter = ['meter_type', 'size', 'brand']
    search_fields = ['serial_number', 'asset__asset_id', 'customer_account']
    
    
@admin.register(AssetPhoto)
class AssetPhotoAdmin(admin.ModelAdmin):
    list_display = ['asset', 'caption', 'taken_by', 'taken_at']
    list_filter = ['taken_at']
    search_fields = ['asset__asset_id', 'caption']
    raw_id_fields = ['asset']


@admin.register(AssetInspection)
class AssetInspectionAdmin(admin.ModelAdmin):
    list_display = [
        'asset', 'inspection_date', 'inspector', 'condition_rating',
        'requires_maintenance', 'maintenance_priority'
    ]
    list_filter = [
        'condition_rating', 'requires_maintenance', 
        'maintenance_priority', 'inspection_date'
    ]
    search_fields = ['asset__asset_id', 'asset__name', 'notes']
    raw_id_fields = ['asset']