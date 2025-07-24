"""
File: accesswash_platform/core/email_service.py
Complete enhanced email service with robust error handling
"""

import logging
from typing import List, Dict, Any, Optional
from django.core.mail import EmailMultiAlternatives, send_mail, get_connection
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.conf import settings
from django.utils.html import strip_tags
from django.db import connection
import smtplib

logger = logging.getLogger('core.email_service')


class EmailService:
    """Enhanced email service with multi-tenant support"""
    
    def __init__(self):
        self.default_from_email = settings.DEFAULT_FROM_EMAIL
        self.platform_url = getattr(settings, 'PLATFORM_URL', 'https://api.accesswash.org')
        self._validate_email_config()
    
    def _validate_email_config(self):
        """Validate email configuration on startup"""
        try:
            if settings.EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
                # Test SMTP connection
                connection = get_connection()
                connection.open()
                connection.close()
                logger.info("✅ Email configuration validated successfully")
            else:
                logger.info("📧 Using console email backend for development")
        except Exception as e:
            logger.warning(f"⚠️  Email configuration test failed: {e}")
    
    def get_tenant_context(self) -> Dict[str, Any]:
        """Get tenant-specific context with fallback handling"""
        try:
            # Get current connection info
            tenant = getattr(connection, 'tenant', None)
            schema_name = getattr(connection, 'schema_name', 'public')
            
            # Public schema context
            if not tenant or schema_name == 'public':
                return self._get_platform_context()
            
            # Try tenant-specific context
            try:
                return self._get_tenant_context(tenant)
            except Exception as e:
                logger.warning(f"Failed to get tenant context: {e}")
                return self._get_fallback_context(tenant)
                
        except Exception as e:
            logger.error(f"Error in get_tenant_context: {e}")
            return self._get_default_context()
    
    def _get_platform_context(self) -> Dict[str, Any]:
        """Platform-level email context"""
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
            'tenant_schema': 'public',
        }
    
    def _get_tenant_context(self, tenant) -> Dict[str, Any]:
        """Tenant-specific email context"""
        from core.models import UtilitySettings
        
        # Get tenant domain
        tenant_domain = self._build_tenant_domain(tenant)
        
        # Try to get utility settings
        utility_settings = UtilitySettings.objects.first()
        
        if utility_settings:
            from_email = self.default_from_email
            if utility_settings.contact_email:
                from_email = f"{utility_settings.utility_name} <{utility_settings.contact_email}>"
            
            return {
                'is_platform_email': False,
                'utility_name': utility_settings.utility_name,
                'utility_logo': utility_settings.logo.url if utility_settings.logo else None,
                'primary_color': utility_settings.primary_color,
                'secondary_color': utility_settings.secondary_color,
                'contact_phone': utility_settings.contact_phone or '',
                'contact_email': utility_settings.contact_email or settings.ADMIN_EMAIL,
                'website': utility_settings.website or tenant_domain,
                'frontend_url': tenant_domain,
                'from_email': from_email,
                'address': utility_settings.address or '',
                'tenant_schema': tenant.schema_name,
            }
        
        return self._get_fallback_context(tenant)
    
    def _get_fallback_context(self, tenant) -> Dict[str, Any]:
        """Fallback context when tenant settings unavailable"""
        tenant_domain = self._build_tenant_domain(tenant)
        
        return {
            'is_platform_email': False,
            'utility_name': getattr(tenant, 'name', 'Water Utility'),
            'utility_logo': None,
            'primary_color': '#2563eb',
            'secondary_color': '#1e40af',
            'contact_phone': '',
            'contact_email': settings.ADMIN_EMAIL,
            'website': tenant_domain,
            'frontend_url': tenant_domain,
            'from_email': self.default_from_email,
            'address': '',
            'tenant_schema': getattr(tenant, 'schema_name', 'unknown'),
        }
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Ultimate fallback context"""
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
            'tenant_schema': 'unknown',
        }
    
    def _build_tenant_domain(self, tenant) -> str:
        """Build tenant domain URL"""
        try:
            if hasattr(tenant, 'domains'):
                primary_domain = tenant.domains.filter(is_primary=True, is_active=True).first()
                if primary_domain:
                    protocol = 'https' if not settings.DEBUG else 'http'
                    port = '' if not settings.DEBUG else ':8000'
                    return f"{protocol}://{primary_domain.domain}{port}"
        except Exception as e:
            logger.warning(f"Could not build tenant domain: {e}")
        
        return self.platform_url
    
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
        Send email with template and error handling
        
        Args:
            template_name: Template name without extension
            context: Template context variables
            to_emails: List of recipient emails
            subject: Email subject (optional)
            from_email: Sender email (optional)
            reply_to: Reply-to emails (optional)
            attachments: List of attachments (optional)
        
        Returns:
            bool: True if sent successfully
        """
        try:
            # Merge with tenant context
            tenant_context = self.get_tenant_context()
            full_context = {
                **tenant_context,
                **context,
                'support_email': settings.ADMIN_EMAIL,
            }
            
            # Render templates
            html_content = self._render_html_template(template_name, full_context)
            text_content = self._render_text_template(template_name, full_context, html_content)
            
            # Determine subject and from_email
            email_subject = subject or full_context.get('email_subject', 'Notification from AccessWash')
            email_from = from_email or full_context.get('from_email', self.default_from_email)
            
            # Create and send email
            email = EmailMultiAlternatives(
                subject=email_subject,
                body=text_content,
                from_email=email_from,
                to=to_emails,
                reply_to=reply_to
            )
            
            email.attach_alternative(html_content, "text/html")
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    email.attach(
                        attachment['filename'],
                        attachment['content'],
                        attachment.get('mimetype', 'application/octet-stream')
                    )
            
            # Send email
            result = email.send(fail_silently=False)
            
            if result:
                logger.info(f"📧 Email sent: {template_name} to {', '.join(to_emails)}")
                return True
            else:
                logger.error(f"❌ Failed to send email: {template_name} to {', '.join(to_emails)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Email error ({template_name}): {e}")
            return False
    
    def _render_html_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render HTML email template with fallback"""
        try:
            html_template = f'emails/{template_name}.html'
            return render_to_string(html_template, context)
        except TemplateDoesNotExist:
            logger.warning(f"HTML template not found: emails/{template_name}.html")
            return self._create_fallback_html(context)
    
    def _render_text_template(self, template_name: str, context: Dict[str, Any], html_content: str) -> str:
        """Render text email template with fallback"""
        try:
            text_template = f'emails/{template_name}.txt'
            return render_to_string(text_template, context)
        except TemplateDoesNotExist:
            # Strip HTML tags as fallback
            return strip_tags(html_content)
    
    def _create_fallback_html(self, context: Dict[str, Any]) -> str:
        """Create basic HTML email when template is missing"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{context.get('email_subject', 'AccessWash Notification')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {context.get('primary_color', '#2563eb')}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{context.get('utility_name', 'AccessWash Platform')}</h1>
                </div>
                <div class="content">
                    <p>This is a notification from {context.get('utility_name', 'AccessWash Platform')}.</p>
                    <p>If you have any questions, please contact us at {context.get('contact_email', 'support@accesswash.org')}.</p>
                </div>
                <div class="footer">
                    <p>&copy; {context.get('utility_name', 'AccessWash Platform')}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def send_test_email(self, to_email: str) -> bool:
        """Send test email to verify configuration"""
        context = {
            'test_message': 'This is a test email from AccessWash Platform.',
            'email_subject': 'AccessWash Email Test - Configuration Working'
        }
        
        return self.send_email(
            template_name='admin/test_email',
            context=context,
            to_emails=[to_email]
        )
    
    def send_user_invitation(self, invitation, password=None) -> bool:
        """Send user invitation email"""
        tenant_context = self.get_tenant_context()
        
        context = {
            'invitation': invitation,
            'user_email': invitation.email,
            'user_role': invitation.get_role_display(),
            'invited_by': invitation.invited_by.get_full_name() if invitation.invited_by else 'Administrator',
            'invitation_url': f"{tenant_context['frontend_url']}/auth/accept-invitation/{invitation.token}/",
            'expires_on': invitation.expires_on,
            'password': password,
            'email_subject': f'You\'re invited to join {tenant_context["utility_name"]}'
        }
        
        template = 'auth/invitation_with_password' if password else 'auth/invitation'
        
        return self.send_email(
            template_name=template,
            context=context,
            to_emails=[invitation.email]
        )
    
    def send_password_reset(self, user, reset_url: str) -> bool:
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
    
    def send_password_changed(self, user) -> bool:
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
    
    def send_account_activated(self, user) -> bool:
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


# Global email service instance
email_service = EmailService()