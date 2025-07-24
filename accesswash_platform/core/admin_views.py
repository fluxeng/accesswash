"""
Admin views for email testing and management
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.conf import settings
from core.email_service import email_service
import logging

logger = logging.getLogger(__name__)


@staff_member_required
def email_test_view(request):
    """View for testing email functionality"""
    if request.method == 'POST':
        email = request.POST.get('email')
        test_type = request.POST.get('test_type', 'service')
        
        if not email:
            messages.error(request, 'Email address is required')
            return render(request, 'admin/email_test.html')
        
        success = False
        error_message = None
        
        try:
            if test_type == 'django':
                # Test basic Django email
                result = send_mail(
                    subject='AccessWash Platform - Django Email Test',
                    message='This is a test email sent using Django\'s send_mail function.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                success = bool(result)
                
            elif test_type == 'service':
                # Test EmailService
                success = email_service.send_test_email(email)
            
            if success:
                messages.success(request, f'Test email sent successfully to {email}')
                logger.info(f'Admin test email sent successfully to {email} using {test_type}')
            else:
                messages.error(request, f'Failed to send email to {email}')
                logger.error(f'Admin test email failed to {email} using {test_type}')
                
        except Exception as e:
            error_message = str(e)
            messages.error(request, f'Email error: {error_message}')
            logger.error(f'Admin test email error to {email}: {error_message}')
        
        return render(request, 'admin/email_test.html', {
            'email': email,
            'test_type': test_type,
            'success': success,
            'error_message': error_message,
        })
    
    # GET request - show the form
    context = {
        'title': 'Email Test',
        'email_backend': settings.EMAIL_BACKEND,
        'email_host': getattr(settings, 'EMAIL_HOST', 'Not configured'),
        'email_port': getattr(settings, 'EMAIL_PORT', 'Not configured'),
        'email_user': getattr(settings, 'EMAIL_HOST_USER', 'Not configured'),
        'default_from_email': settings.DEFAULT_FROM_EMAIL,
    }
    
    return render(request, 'admin/email_test.html', context)


@staff_member_required
@csrf_protect
@require_POST
def send_test_invitation(request):
    """Send a test invitation email"""
    email = request.POST.get('email')
    role = request.POST.get('role', 'field_tech')
    
    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required'})
    
    try:
        # Create a mock invitation object
        from users.models import UserInvitation, User
        from django.utils import timezone
        from datetime import timedelta
        import uuid
        
        # Create a mock invitation for testing
        class MockInvitation:
            def __init__(self, email, role, invited_by):
                self.email = email
                self.role = role
                self.invited_by = invited_by
                self.expires_on = timezone.now() + timedelta(days=7)
                self.token = str(uuid.uuid4())
            
            def get_role_display(self):
                role_choices = {
                    'admin': 'Administrator',
                    'supervisor': 'Supervisor', 
                    'field_tech': 'Field Technician',
                    'customer_service': 'Customer Service'
                }
                return role_choices.get(self.role, self.role)
        
        # Create temporary invitation for testing
        invitation = MockInvitation(email, role, request.user)
        
        # Send invitation email
        success = email_service.send_user_invitation(invitation, password='TestPassword123!')
        
        if success:
            logger.info(f'Test invitation sent to {email}')
            return JsonResponse({
                'success': True, 
                'message': f'Test invitation sent to {email}'
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'Failed to send invitation email'
            })
            
    except Exception as e:
        logger.error(f'Error sending test invitation to {email}: {e}')
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })


@staff_member_required
def email_config_view(request):
    """View email configuration details"""
    config = {
        'EMAIL_BACKEND': settings.EMAIL_BACKEND,
        'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'Not set'),
        'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'Not set'),
        'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', False),
        'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', False),
        'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', 'Not set'),
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        'ADMIN_EMAIL': getattr(settings, 'ADMIN_EMAIL', 'Not set'),
        'PLATFORM_URL': getattr(settings, 'PLATFORM_URL', 'Not set'),
    }
    
    return render(request, 'admin/email_config.html', {'config': config})