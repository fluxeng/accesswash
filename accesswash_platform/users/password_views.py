"""
Password reset views for AccessWash platform
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
import logging

from .models import User
from .serializers import ForgotPasswordSerializer, ResetPasswordSerializer
from core.email_service import email_service

logger = logging.getLogger(__name__)


class ForgotPasswordView(APIView):
    """Request password reset"""
    permission_classes = []
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # This will send the email if user exists
        result = serializer.save()
        
        # Always return success for security (don't reveal if email exists)
        return Response({
            'success': True,
            'message': 'If an account with this email exists, a password reset link has been sent.'
        })


class ResetPasswordView(APIView):
    """Reset password with token"""
    permission_classes = []
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Password has been reset successfully.'
        })


class TestEmailView(APIView):
    """Test email functionality (admin only)"""
    permission_classes = []  # We'll check manually
    
    def post(self, request):
        # Check if user is admin
        if not (request.user.is_authenticated and request.user.is_staff):
            return Response({
                'success': False,
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        email = request.data.get('email')
        if not email:
            return Response({
                'success': False,
                'error': 'Email address is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            success = email_service.send_test_email(email)
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Test email sent successfully to {email}'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to send test email'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f'Test email error: {e}')
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)