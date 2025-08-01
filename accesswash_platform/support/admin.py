from django.contrib import admin
from django.utils.html import format_html
from django.db import connection
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import ServiceRequest, ServiceRequestComment, ServiceRequestPhoto


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


class ServiceRequestCommentInline(admin.TabularInline):
    """Inline admin for service request comments"""
    model = ServiceRequestComment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = [
        'author_customer', 'author_staff', 'comment', 
        'is_internal', 'status_changed_from', 'status_changed_to', 'created_at'
    ]
    
    def get_queryset(self, request):
        """Order comments by creation time"""
        return super().get_queryset(request).order_by('created_at')


class ServiceRequestPhotoInline(admin.TabularInline):
    """Inline admin for service request photos"""
    model = ServiceRequestPhoto
    extra = 0
    readonly_fields = ['uploaded_at', 'file_size', 'image_width', 'image_height', 'photo_preview']
    fields = [
        'photo', 'photo_preview', 'caption', 'uploaded_by_customer', 
        'uploaded_by_staff', 'file_size', 'uploaded_at'
    ]
    
    def photo_preview(self, obj):
        """Show small photo preview"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; '
                'object-fit: cover; border-radius: 4px;" />',
                obj.photo.url
            )
        return "No photo"
    photo_preview.short_description = 'Preview'


@admin.register(ServiceRequest)
class ServiceRequestAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for service requests"""
    
    list_display = [
        'request_number', 'customer_info', 'issue_type_badge', 'title_truncated',
        'status_badge', 'urgency_badge', 'assigned_to_info',
        'created_at_formatted', 'priority_score', 'sla_status'
    ]
    list_filter = [
        'issue_type', 'status', 'urgency', 'created_at',
        'assigned_to', 'resolution_category', 'customer_rating'
    ]
    search_fields = [
        'request_number', 'title', 'description',
        'customer__email', 'customer__first_name', 'customer__last_name',
        'customer__account_number'
    ]
    readonly_fields = [
        'id', 'request_number', 'priority_score', 'created_at', 'updated_at',
        'target_response_time', 'target_resolution_time', 'actual_response_time',
        'customer_info_detail', 'location_map', 'sla_tracking', 'request_timeline'
    ]
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'request_number', 'customer_info_detail', 'issue_type', 'title',
                'description', 'urgency', 'priority_score'
            )
        }),
        ('Location Details', {
            'fields': ('reported_location', 'location_coordinates', 'location_map', 'related_asset'),
            'classes': ('wide',)
        }),
        ('Assignment & Status', {
            'fields': (
                'status', 'assigned_to', 'assigned_at',
                'acknowledged_at', 'resolved_at', 'closed_at'
            )
        }),
        ('Resolution', {
            'fields': (
                'resolution_notes', 'resolution_category',
                'customer_rating', 'customer_feedback'
            ),
            'classes': ('collapse',)
        }),
        ('Work Order Integration', {
            'fields': ('created_work_order', 'work_order_number'),
            'classes': ('collapse',)
        }),
        ('SLA & Performance Tracking', {
            'fields': (
                'sla_tracking', 'target_response_time', 'target_resolution_time',
                'actual_response_time', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        ('Request Timeline', {
            'fields': ('request_timeline',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ServiceRequestCommentInline, ServiceRequestPhotoInline]
    
    # Custom display methods
    def customer_info(self, obj):
        """Display customer information with link"""
        customer = obj.customer
        return format_html(
            '<strong>{}</strong><br>'
            '<small>{}</small><br>'
            '<small>Acc: {}</small>',
            customer.get_full_name(),
            customer.email,
            customer.account_number
        )
    customer_info.short_description = 'Customer'
    
    def customer_info_detail(self, obj):
        """Detailed customer information for form"""
        customer = obj.customer
        return format_html(
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">'
            '<h4 style="margin-top: 0;">Customer Details</h4>'
            '<p><strong>Name:</strong> {}</p>'
            '<p><strong>Email:</strong> <a href="mailto:{}">{}</a></p>'
            '<p><strong>Phone:</strong> {}</p>'
            '<p><strong>Account Number:</strong> {}</p>'
            '<p><strong>Service Address:</strong> {}</p>'
            '<p><strong>Service Type:</strong> {}</p>'
            '</div>',
            customer.get_full_name(),
            customer.email, customer.email,
            customer.phone_number or 'Not provided',
            customer.account_number,
            customer.property_address,
            customer.get_service_type_display()
        )
    customer_info_detail.short_description = 'Customer Information'
    
    def issue_type_badge(self, obj):
        """Display issue type with color coding"""
        colors = {
            'no_water': '#dc3545',
            'low_pressure': '#fd7e14', 
            'pipe_burst': '#dc3545',
            'water_quality': '#6610f2',
            'meter_problem': '#17a2b8',
            'billing_inquiry': '#28a745',
            'connection_request': '#007bff',
            'disconnection': '#6c757d',
            'other': '#6c757d'
        }
        color = colors.get(obj.issue_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_issue_type_display()
        )
    issue_type_badge.short_description = 'Issue Type'
    
    def title_truncated(self, obj):
        """Display truncated title with tooltip"""
        if len(obj.title) > 30:
            return format_html(
                '<span title="{}">{}</span>',
                obj.title,
                obj.title[:30] + '...'
            )
        return obj.title
    title_truncated.short_description = 'Title'
    
    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'open': '#dc3545',
            'acknowledged': '#fd7e14',
            'assigned': '#007bff',
            'in_progress': '#6610f2',
            'on_hold': '#6c757d',
            'resolved': '#28a745',
            'closed': '#198754',
            'cancelled': '#343a40'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def urgency_badge(self, obj):
        """Display urgency with color coding"""
        colors = {
            'emergency': '#dc3545',
            'high': '#fd7e14',
            'standard': '#007bff',
            'low': '#28a745'
        }
        color = colors.get(obj.urgency, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_urgency_display()
        )
    urgency_badge.short_description = 'Urgency'
    
    def assigned_to_info(self, obj):
        """Display assigned staff with status"""
        if obj.assigned_to:
            return format_html(
                '<strong>{}</strong><br>'
                '<small>{}</small>',
                obj.assigned_to.get_full_name(),
                obj.assigned_to.get_role_display()
            )
        return format_html('<span style="color: #dc3545;">Unassigned</span>')
    assigned_to_info.short_description = 'Assigned To'
    
    def created_at_formatted(self, obj):
        """Format creation date with relative time"""
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return format_html(
                '{}<br><small>{} days ago</small>',
                obj.created_at.strftime('%Y-%m-%d %H:%M'),
                diff.days
            )
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return format_html(
                '{}<br><small>{} hours ago</small>',
                obj.created_at.strftime('%Y-%m-%d %H:%M'),
                hours
            )
        else:
            minutes = diff.seconds // 60
            return format_html(
                '{}<br><small>{} min ago</small>',
                obj.created_at.strftime('%Y-%m-%d %H:%M'),
                minutes
            )
    created_at_formatted.short_description = 'Created'
    
    def sla_status(self, obj):
        """Display SLA status"""
        if obj.status in ['resolved', 'closed', 'cancelled']:
            return format_html('<span style="color: #28a745;">✓ Complete</span>')
        
        if obj.target_resolution_time:
            now = timezone.now()
            if now > obj.target_resolution_time:
                return format_html('<span style="color: #dc3545;">⚠ Overdue</span>')
            else:
                time_left = obj.target_resolution_time - now
                if time_left.total_seconds() < 3600:  # Less than 1 hour
                    return format_html('<span style="color: #fd7e14;">⏰ Due Soon</span>')
                else:
                    return format_html('<span style="color: #28a745;">✓ On Time</span>')
        
        return format_html('<span style="color: #6c757d;">— N/A</span>')
    sla_status.short_description = 'SLA Status'
    
    def location_map(self, obj):
        """Display location on map if coordinates available"""
        if obj.location_coordinates:
            lat = obj.location_coordinates.y
            lng = obj.location_coordinates.x
            return format_html(
                '<div style="margin: 10px 0;">'
                '<p><strong>Coordinates:</strong> {:.6f}, {:.6f}</p>'
                '<a href="https://www.google.com/maps?q={},{}" target="_blank" '
                'style="display: inline-block; padding: 8px 12px; background: #007bff; '
                'color: white; text-decoration: none; border-radius: 4px;">'
                '📍 View on Google Maps</a>'
                '</div>',
                lat, lng, lat, lng
            )
        return "No coordinates provided"
    location_map.short_description = 'Location'
    
    def sla_tracking(self, obj):
        """Display SLA tracking information"""
        html_parts = []
        
        # Response time
        if obj.target_response_time:
            if obj.actual_response_time:
                response_diff = obj.actual_response_time - obj.created_at
                target_diff = obj.target_response_time - obj.created_at
                
                if response_diff <= target_diff:
                    status_color = '#28a745'
                    status_text = '✓ Met'
                else:
                    status_color = '#dc3545'
                    status_text = '✗ Missed'
                
                html_parts.append(f'''
                    <p><strong>Response SLA:</strong> 
                    <span style="color: {status_color};">{status_text}</span></p>
                    <p>Target: {target_diff.total_seconds() / 3600:.1f} hours</p>
                    <p>Actual: {response_diff.total_seconds() / 3600:.1f} hours</p>
                ''')
            else:
                now = timezone.now()
                elapsed = now - obj.created_at
                target = obj.target_response_time - obj.created_at
                
                if elapsed > target:
                    status_color = '#dc3545'
                    status_text = '⚠ Overdue'
                else:
                    status_color = '#fd7e14'
                    status_text = '⏰ Pending'
                
                html_parts.append(f'''
                    <p><strong>Response SLA:</strong> 
                    <span style="color: {status_color};">{status_text}</span></p>
                    <p>Target: {target.total_seconds() / 3600:.1f} hours</p>
                    <p>Elapsed: {elapsed.total_seconds() / 3600:.1f} hours</p>
                ''')
        
        # Resolution time
        if obj.target_resolution_time:
            if obj.resolved_at:
                resolution_diff = obj.resolved_at - obj.created_at
                target_diff = obj.target_resolution_time - obj.created_at
                
                if resolution_diff <= target_diff:
                    status_color = '#28a745'
                    status_text = '✓ Met'
                else:
                    status_color = '#dc3545'
                    status_text = '✗ Missed'
                
                html_parts.append(f'''
                    <p><strong>Resolution SLA:</strong> 
                    <span style="color: {status_color};">{status_text}</span></p>
                    <p>Target: {target_diff.days} days</p>
                    <p>Actual: {resolution_diff.days} days</p>
                ''')
            else:
                now = timezone.now()
                elapsed = now - obj.created_at
                target = obj.target_resolution_time - obj.created_at
                
                if elapsed > target:
                    status_color = '#dc3545'
                    status_text = '⚠ Overdue'
                else:
                    status_color = '#28a745'
                    status_text = '✓ On Track'
                
                html_parts.append(f'''
                    <p><strong>Resolution SLA:</strong> 
                    <span style="color: {status_color};">{status_text}</span></p>
                    <p>Target: {target.days} days</p>
                    <p>Elapsed: {elapsed.days} days</p>
                ''')
        
        if html_parts:
            return format_html(
                '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">{}</div>',
                ''.join(html_parts)
            )
        
        return "No SLA data available"
    sla_tracking.short_description = 'SLA Tracking'
    
    def request_timeline(self, obj):
        """Display request timeline"""
        timeline_items = []
        
        # Created
        timeline_items.append({
            'event': 'Created',
            'timestamp': obj.created_at,
            'actor': obj.customer.get_full_name(),
            'description': f'Request {obj.request_number} created'
        })
        
        # Acknowledged
        if obj.acknowledged_at:
            timeline_items.append({
                'event': 'Acknowledged',
                'timestamp': obj.acknowledged_at,
                'actor': 'System',
                'description': 'Request acknowledged'
            })
        
        # Assigned
        if obj.assigned_at and obj.assigned_to:
            timeline_items.append({
                'event': 'Assigned',
                'timestamp': obj.assigned_at,
                'actor': obj.assigned_to.get_full_name(),
                'description': f'Assigned to {obj.assigned_to.get_full_name()}'
            })
        
        # Comments
        for comment in obj.comments.all().order_by('created_at'):
            timeline_items.append({
                'event': 'Comment',
                'timestamp': comment.created_at,
                'actor': comment.get_author_name(),
                'description': comment.comment[:100] + ('...' if len(comment.comment) > 100 else '')
            })
        
        # Resolved
        if obj.resolved_at:
            timeline_items.append({
                'event': 'Resolved',
                'timestamp': obj.resolved_at,
                'actor': obj.assigned_to.get_full_name() if obj.assigned_to else 'System',
                'description': 'Request resolved'
            })
        
        # Closed
        if obj.closed_at:
            timeline_items.append({
                'event': 'Closed',
                'timestamp': obj.closed_at,
                'actor': 'System',
                'description': 'Request closed'
            })
        
        # Sort by timestamp
        timeline_items.sort(key=lambda x: x['timestamp'])
        
        # Generate HTML
        html_parts = ['<div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">']
        html_parts.append('<h4 style="margin-top: 0;">Request Timeline</h4>')
        
        for item in timeline_items:
            html_parts.append(f'''
                <div style="margin-bottom: 10px; padding: 8px; border-left: 3px solid #007bff; background: white;">
                    <strong>{item['event']}</strong> by {item['actor']}<br>
                    <small style="color: #6c757d;">{item['timestamp'].strftime('%Y-%m-%d %H:%M')}</small><br>
                    {item['description']}
                </div>
            ''')
        
        html_parts.append('</div>')
        
        return format_html(''.join(html_parts))
    request_timeline.short_description = 'Timeline'
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related(
            'customer', 'assigned_to', 'related_asset'
        ).prefetch_related('comments', 'photos')
    
    # Custom actions
    actions = [
        'mark_acknowledged', 'mark_in_progress', 'mark_resolved', 
        'assign_to_me', 'bulk_assign', 'export_to_csv'
    ]
    
    def mark_acknowledged(self, request, queryset):
        """Mark selected requests as acknowledged"""
        count = 0
        for obj in queryset.filter(status='open'):
            obj.acknowledge()
            count += 1
        self.message_user(request, f'{count} requests marked as acknowledged.')
    mark_acknowledged.short_description = "Mark selected requests as acknowledged"
    
    def mark_in_progress(self, request, queryset):
        """Mark selected requests as in progress"""
        count = queryset.filter(
            status__in=['open', 'acknowledged', 'assigned']
        ).update(status='in_progress')
        self.message_user(request, f'{count} requests marked as in progress.')
    mark_in_progress.short_description = "Mark selected requests as in progress"
    
    def mark_resolved(self, request, queryset):
        """Mark selected requests as resolved"""
        count = 0
        for obj in queryset.exclude(status__in=['resolved', 'closed', 'cancelled']):
            obj.resolve()
            count += 1
        self.message_user(request, f'{count} requests marked as resolved.')
    mark_resolved.short_description = "Mark selected requests as resolved"
    
    def assign_to_me(self, request, queryset):
        """Assign selected requests to current user"""
        count = 0
        for obj in queryset.filter(assigned_to__isnull=True):
            obj.assign_to_staff(request.user)
            count += 1
        self.message_user(request, f'{count} requests assigned to you.')
    assign_to_me.short_description = "Assign selected requests to me"
    
    def bulk_assign(self, request, queryset):
        """Bulk assign requests (would need additional form)"""
        # This would typically open a form to select assignee
        self.message_user(request, "Bulk assignment feature not yet implemented.")
    bulk_assign.short_description = "Bulk assign requests"
    
    def export_to_csv(self, request, queryset):
        """Export selected requests to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="service_requests.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Request Number', 'Customer', 'Issue Type', 'Status', 
            'Urgency', 'Created', 'Assigned To', 'Priority Score'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.request_number,
                obj.customer.get_full_name(),
                obj.get_issue_type_display(),
                obj.get_status_display(),
                obj.get_urgency_display(),
                obj.created_at.strftime('%Y-%m-%d %H:%M'),
                obj.assigned_to.get_full_name() if obj.assigned_to else 'Unassigned',
                obj.priority_score
            ])
        
        return response
    export_to_csv.short_description = "Export selected requests to CSV"


@admin.register(ServiceRequestComment)
class ServiceRequestCommentAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for service request comments"""
    
    list_display = [
        'service_request_info', 'author_info', 'comment_preview',
        'is_internal', 'status_change_info', 'created_at'
    ]
    list_filter = ['is_internal', 'created_at', 'service_request__status']
    search_fields = [
        'service_request__request_number', 'comment',
        'author_customer__email', 'author_staff__email'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def service_request_info(self, obj):
        """Display service request info"""
        return format_html(
            '<a href="{}">{}</a><br>'
            '<small>{}</small>',
            reverse('admin:support_servicerequest_change', args=[obj.service_request.pk]),
            obj.service_request.request_number,
            obj.service_request.title[:30] + ('...' if len(obj.service_request.title) > 30 else '')
        )
    service_request_info.short_description = 'Service Request'
    
    def author_info(self, obj):
        """Display comment author"""
        author_name = obj.get_author_name()
        author_type = obj.get_author_type()
        
        color = '#007bff' if author_type == 'customer' else '#28a745'
        
        return format_html(
            '<strong>{}</strong><br>'
            '<span style="color: {}; font-size: 11px;">{}</span>',
            author_name,
            color,
            author_type.title()
        )
    author_info.short_description = 'Author'
    
    def comment_preview(self, obj):
        """Display comment preview"""
        if len(obj.comment) > 50:
            return format_html(
                '<span title="{}">{}</span>',
                obj.comment,
                obj.comment[:50] + '...'
            )
        return obj.comment
    comment_preview.short_description = 'Comment'
    
    def status_change_info(self, obj):
        """Display status change information"""
        if obj.status_changed_from and obj.status_changed_to:
            return format_html(
                '<span style="color: #dc3545;">{}</span> → '
                '<span style="color: #28a745;">{}</span>',
                obj.status_changed_from.title(),
                obj.status_changed_to.title()
            )
        return '—'
    status_change_info.short_description = 'Status Change'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'service_request', 'author_customer', 'author_staff'
        )


@admin.register(ServiceRequestPhoto)
class ServiceRequestPhotoAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """Admin interface for service request photos"""
    
    list_display = [
        'service_request_info', 'photo_thumbnail', 'caption_preview',
        'uploader_info', 'file_info', 'uploaded_at'
    ]
    list_filter = ['uploaded_at']
    search_fields = [
        'service_request__request_number', 'caption',
        'uploaded_by_customer__email', 'uploaded_by_staff__email'
    ]
    readonly_fields = [
        'uploaded_at', 'file_size', 'image_width', 'image_height'
    ]
    
    def service_request_info(self, obj):
        """Display service request info"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:support_servicerequest_change', args=[obj.service_request.pk]),
            obj.service_request.request_number
        )
    service_request_info.short_description = 'Service Request'
    
    def photo_thumbnail(self, obj):
        """Display photo thumbnail"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 80px; height: 80px; '
                'object-fit: cover; border-radius: 4px; border: 1px solid #ddd;" />',
                obj.photo.url
            )
        return "No photo"
    photo_thumbnail.short_description = 'Photo'
    
    def caption_preview(self, obj):
        """Display caption preview"""
        if obj.caption:
            if len(obj.caption) > 30:
                return format_html(
                    '<span title="{}">{}</span>',
                    obj.caption,
                    obj.caption[:30] + '...'
                )
            return obj.caption
        return '—'
    caption_preview.short_description = 'Caption'
    
    def uploader_info(self, obj):
        """Display uploader information"""
        uploader_name = obj.get_uploader_name()
        uploader_type = 'customer' if obj.uploaded_by_customer else 'staff'
        
        color = '#007bff' if uploader_type == 'customer' else '#28a745'
        
        return format_html(
            '<strong>{}</strong><br>'
            '<span style="color: {}; font-size: 11px;">{}</span>',
            uploader_name,
            color,
            uploader_type.title()
        )
    uploader_info.short_description = 'Uploaded By'
    
    def file_info(self, obj):
        """Display file information"""
        info_parts = []
        
        if obj.file_size:
            if obj.file_size > 1024 * 1024:
                size_str = f"{obj.file_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{obj.file_size / 1024:.1f} KB"
            info_parts.append(f"Size: {size_str}")
        
        if obj.image_width and obj.image_height:
            info_parts.append(f"Dimensions: {obj.image_width}×{obj.image_height}")
        
        return format_html('<br>'.join(info_parts)) if info_parts else '—'
    file_info.short_description = 'File Info'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'service_request', 'uploaded_by_customer', 'uploaded_by_staff'
        )


# Custom admin site configuration
admin.site.site_header = "AccessWash Customer Support"
admin.site.site_title = "Support Admin"
admin.site.index_title = "Customer Service Management"