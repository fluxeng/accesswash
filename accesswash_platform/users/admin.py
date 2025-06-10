from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User, UserInvitation


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""
    
    list_display = [
        'email', 'get_full_name', 'role', 'employee_id',
        'is_active', 'is_deleted', 'last_active_display'
    ]
    list_filter = [
        'role', 'is_active', 'is_deleted', 'is_staff',
        'date_joined', 'last_active'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'employee_id']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'employee_id', 'phone_number')
        }),
        ('Role & Permissions', {
            'fields': ('role', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Profile', {
            'fields': ('avatar', 'location_tracking_consent', 'notification_preferences')
        }),
        ('Status', {
            'fields': ('is_active', 'is_deleted', 'deleted_on')
        }),
        ('Activity', {
            'fields': ('last_active', 'last_location', 'date_joined', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'first_name',
                'last_name', 'employee_id', 'role'
            ),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_active', 'created_by', 'deleted_on']
    
    def last_active_display(self, obj):
        """Display last active with color coding"""
        if not obj.last_active:
            return mark_safe('<span style="color: gray;">Never</span>')
        
        from django.utils import timezone
        diff = timezone.now() - obj.last_active
        
        if diff.days > 30:
            color = 'red'
        elif diff.days > 7:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.last_active.strftime('%Y-%m-%d %H:%M')
        )
    
    last_active_display.short_description = 'Last Active'
    
    def get_queryset(self, request):
        """Include deleted users if requested"""
        qs = super().get_queryset(request)
        if request.GET.get('show_deleted'):
            return qs
        return qs.filter(is_deleted=False)
    
    actions = ['activate_users', 'deactivate_users', 'soft_delete_users']
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} users activated.')
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} users deactivated.')
    
    def soft_delete_users(self, request, queryset):
        """Soft delete selected users"""
        from django.utils import timezone
        count = queryset.update(
            is_deleted=True,
            is_active=False,
            deleted_on=timezone.now()
        )
        self.message_user(request, f'{count} users soft deleted.')


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    """Admin interface for UserInvitation model"""
    
    list_display = [
        'email', 'role', 'invited_by', 'status_display',
        'created_on', 'expires_on'
    ]
    list_filter = ['role', 'is_accepted', 'created_on', 'expires_on']
    search_fields = ['email', 'invited_by__email']
    readonly_fields = [
        'token', 'invited_by', 'is_accepted', 'accepted_on', 'created_on'
    ]
    
    def status_display(self, obj):
        """Display invitation status with color"""
        if obj.is_accepted:
            return format_html(
                '<span style="color: green;">✓ Accepted</span>'
            )
        elif obj.is_valid():
            return format_html(
                '<span style="color: orange;">⏳ Pending</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Expired</span>'
            )
    
    status_display.short_description = 'Status'
    
    actions = ['resend_invitations']
    
    def resend_invitations(self, request, queryset):
        """Resend selected invitations"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Only resend pending invitations
        pending = queryset.filter(is_accepted=False)
        count = pending.update(expires_on=timezone.now() + timedelta(days=7))
        
        # TODO: Actually send the emails
        
        self.message_user(request, f'{count} invitations resent.')