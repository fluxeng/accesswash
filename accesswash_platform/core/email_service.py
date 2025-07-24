"""
AccessWash Email Service
Multi-tenant email handling with templates and utility branding
"""

import logging
from typing import List, Dict, Any, Optional
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.db import connection
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site

logger = logging.getLogger(__name__)


class EmailService:
    """Centralized email service with multi-tenant support"""
    
    def __init__(self):
        self.default_from_email = settings.DEFAULT_FROM_EMAIL
        self.platform_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
    
    def get_tenant_context(self) -> Dict[str, Any]:
        """Get tenant-specific context for email templates"""
        try:
            # Get current tenant info
            tenant = getattr(connection, 'tenant', None)
            
            # Determine if we're in public schema or tenant schema
            is_public_schema = (
                not tenant or 
                getattr(tenant, 'schema_name', None) == 'public' or
                getattr(connection, 'schema_name', None) == 'public'
            )
            
            if is_public_schema:
                # Platform-level context
                return {
                    'is_platform_email': True,
                    'utility_name': 'AccessWash Platform',
                    'utility_logo': None,
                    'primary_color': '#2563eb',
                    'secondary_color': '#1e40af',
                    'contact_phone': '',
                    'contact_email': settings.ADMIN_EMAIL,
                    'website': self.platform_url,
                    'frontend_url': self.platform_url,
                    'from_email': self.default_from_email,
                    'address': '',
                }
            
            # Tenant-specific context
            try:
                from core.models import UtilitySettings
                utility_settings = UtilitySettings.objects.first()
                
                # Get tenant's primary domain
                tenant_domain = None
                if tenant and hasattr(tenant, 'domains'):
                    primary_domain = tenant.domains.filter(is_primary=True, is_active=True).first()
                    if primary_domain:
                        # Use HTTPS in production, HTTP in development
                        protocol = 'https' if not settings.DEBUG else 'http'
                        port = '' if not settings.DEBUG else ':8000'
                        tenant_domain = f"{protocol}://{primary_domain.domain}{port}"
                
                if utility_settings:
                    # Use utility's email if available, otherwise default
                    from_email = self.default_from_email
                    if utility_settings.contact_email:
                        from_email = f"{utility_settings.utility_name} <{utility_settings.contact_email}>"
                    
                    return {
                        'is_platform_email': False,
                        'utility_name': utility_settings.utility_name,
                        'utility_logo': utility_settings.logo.url if utility_settings.logo else None,
                        'primary_color': utility_settings.primary_color,
                        'secondary_color': utility_settings.secondary_color,
                        'contact_phone': utility_settings.contact_phone,
                        'contact_email': utility_settings.contact_email or settings.ADMIN_EMAIL,
                        'website': utility_settings.website or tenant_domain,
                        'frontend_url': tenant_domain or self.platform_url,
                        'from_email': from_email,
                        'address': utility_settings.address,
                        'tenant_schema': tenant.schema_name if tenant else None,
                    }
            except Exception as e:
                logger.warning(f"Could not get utility settings: {e}")
            
            # Fallback tenant context
            tenant_domain = self.platform_url
            if tenant and hasattr(tenant, 'domains'):
                try:
                    primary_domain = tenant.domains.filter(is_primary=True, is_active=True).first()
                    if primary_domain:
                        protocol = 'https' if not settings.DEBUG else 'http'
                        port = '' if not settings.DEBUG else ':8000'
                        tenant_domain = f"{protocol}://{primary_domain.domain}{port}"
                except:
                    pass
            
            return {
                'is_platform_email': False,
                'utility_name': tenant.name if tenant else 'Water Utility',
                'utility_logo': None,
                'primary_color': '#2563eb',
                'secondary_color': '#1e40af',
                'contact_phone': '',
                'contact_email': settings.ADMIN_EMAIL,
                'website': tenant_domain,
                'frontend_url': tenant_domain,
                'from_email': self.default_from_email,
                'address': '',
                'tenant_schema': tenant.schema_name if tenant else None,
            }
            
        except Exception as e:
            logger.error(f"Error getting tenant context: {e}")
            # Ultimate fallback
            return {
                'is_platform_email': True,
                'utility_name': 'AccessWash Platform',
                'utility_logo': None,
                'primary_color': '#2563eb',
                'secondary_color': '#1e40af',
                'contact_phone': '',
                'contact_email': settings.ADMIN_EMAIL,
                'website': self.platform_url,
                'frontend_url': self.platform_url,
                'from_email': self.default_from_email,
                'address': '',
            }
    
    def send_email(
        self,
        template_name: str,
        context: Dict[str, Any],
        to_emails: List[str],
        subject: str = None,
        from_email: str = None,
        reply_to: List[str] = None,
        attachments: List[Dict] = None
    ) -> bool:
        """
        Send an email using templates
        
        Args:
            template_name: Template name (without .html/.txt extension)
            context: Template context variables
            to_emails: List of recipient email addresses
            subject: Email subject (can be overridden by template)
            from_email: Sender email address
            reply_to: Reply-to email addresses
            attachments: List of attachment dicts {'filename': str, 'content': bytes, 'mimetype': str}
        
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Merge with tenant context
            tenant_context = self.get_tenant_context()
            full_context = {
                **tenant_context,
                **context,
                'support_email': settings.ADMIN_EMAIL,
            }
            
            # Render HTML template
            html_template = f'emails/{template_name}.html'
            html_content = render_to_string(html_template, full_context)
            
            # Try to render text template, fall back to stripping HTML
            try:
                text_template = f'emails/{template_name}.txt'
                text_content = render_to_string(text_template, full_context)
            except:
                text_content = strip_tags(html_content)
            
            # Extract subject from context if not provided
            if not subject:
                subject = full_context.get('email_subject', 'Notification from AccessWash')
            
            # Use tenant-specific from email if available
            email_from = from_email or full_context.get('from_email', self.default_from_email)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=email_from,
                to=to_emails,
                reply_to=reply_to
            )
            
            # Attach HTML version
            email.attach_alternative(html_content, "text/html")
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    email.attach(
                        attachment['filename'],
                        attachment['content'],
                        attachment.get('mimetype', 'application/octet-stream')
                    )
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"📧 Email sent: {template_name} to {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email {template_name} to {', '.join(to_emails)}: {e}")
            return False
    
    def send_test_email(self, to_email: str) -> bool:
        """Send a test email to verify email configuration"""
        context = {
            'test_message': 'This is a test email from AccessWash Platform.',
            'email_subject': 'AccessWash Email Test'
        }
        
        return self.send_email(
            template_name='admin/test_email',
            context=context,
            to_emails=[to_email]
        )
    
    def send_user_invitation(self, invitation, password=None):
        """Send user invitation email"""
        tenant_context = self.get_tenant_context()
        
        context = {
            'invitation': invitation,
            'user_email': invitation.email,
            'user_role': invitation.get_role_display(),
            'invited_by': invitation.invited_by.get_full_name() if invitation.invited_by else 'Administrator',
            'invitation_url': f"{tenant_context['frontend_url']}/auth/accept-invitation/{invitation.token}/",
            'expires_on': invitation.expires_on,
            'password': password,  # Only if password was set
            'email_subject': f'You\'re invited to join {tenant_context["utility_name"]}'
        }
        
        template = 'auth/invitation_with_password' if password else 'auth/invitation'
        
        return self.send_email(
            template_name=template,
            context=context,
            to_emails=[invitation.email],
            subject=context['email_subject']
        )
    
    def send_password_reset(self, user, reset_url):
        """Send password reset email"""
        context = {
            'user': user,
            'reset_url': reset_url,
            'email_subject': 'Reset your AccessWash password'
        }
        
        return self.send_email(
            template_name='auth/password_reset',
            context=context,
            to_emails=[user.email]
        )
    
    def send_password_changed(self, user):
        """Send password changed confirmation"""
        context = {
            'user': user,
            'email_subject': 'Your AccessWash password was changed'
        }
        
        return self.send_email(
            template_name='auth/password_changed',
            context=context,
            to_emails=[user.email]
        )
    
    def send_account_activated(self, user):
        """Send account activation confirmation"""
        tenant_context = self.get_tenant_context()
        
        context = {
            'user': user,
            'login_url': f"{tenant_context['frontend_url']}/auth/login/",
            'email_subject': 'Your AccessWash account is now active'
        }
        
        return self.send_email(
            template_name='auth/account_activated',
            context=context,
            to_emails=[user.email]
        )
    
    def send_inspection_reminder(self, asset, inspector):
        """Send asset inspection reminder"""
        tenant_context = self.get_tenant_context()
        
        context = {
            'asset': asset,
            'inspector': inspector,
            'inspect_url': f"{tenant_context['frontend_url']}/admin/",
            'email_subject': f'Inspection Due: {asset.name}'
        }
        
        return self.send_email(
            template_name='operations/inspection_reminder',
            context=context,
            to_emails=[inspector.email]
        )
    
    def send_maintenance_alert(self, asset, assigned_users):
        """Send maintenance required alert"""
        tenant_context = self.get_tenant_context()
        emails = [user.email for user in assigned_users]
        
        context = {
            'asset': asset,
            'asset_url': f"{tenant_context['frontend_url']}/admin/",
            'email_subject': f'Maintenance Required: {asset.name}'
        }
        
        return self.send_email(
            template_name='operations/maintenance_alert',
            context=context,
            to_emails=emails
        )
    
    def send_daily_summary(self, user, summary_data):
        """Send daily work summary to field technician"""
        tenant_context = self.get_tenant_context()
        
        context = {
            'user': user,
            'summary': summary_data,
            'dashboard_url': f"{tenant_context['frontend_url']}/admin/",
            'email_subject': f'Daily Summary - {summary_data.get("date", "Today")}'
        }
        
        return self.send_email(
            template_name='operations/daily_summary',
            context=context,
            to_emails=[user.email]
        )
    
    def send_system_alert(self, alert_type, message, admin_emails=None):
        """Send system alert to administrators"""
        if not admin_emails:
            admin_emails = [settings.ADMIN_EMAIL]
        
        # Always use platform context for system alerts
        context = {
            'alert_type': alert_type,
            'message': message,
            'admin_url': f"{self.platform_url}/admin/",
            'email_subject': f'System Alert: {alert_type}',
            'is_system_alert': True,  # Flag to use platform branding
        }
        
        return self.send_email(
            template_name='admin/system_alert',
            context=context,
            to_emails=admin_emails
        )


# Global email service instance
email_service = EmailService()