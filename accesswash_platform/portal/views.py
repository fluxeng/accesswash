from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
import logging

from .models import Customer, CustomerSession
from .serializers import (
    CustomerRegistrationSerializer, CustomerLoginSerializer,
    CustomerSerializer, CustomerProfileSerializer, CustomerDashboardSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, ChangePasswordSerializer
)
from .authentication import CustomerJWTAuthentication
from .permissions import IsCustomer

logger = logging.getLogger(__name__)


class CustomerRegistrationView(APIView):
    """Customer registration endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Register new customer"""
        serializer = CustomerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            
            # Generate tokens
            tokens = CustomerJWTAuthentication.generate_tokens(customer, request)
            
            # Return customer data with tokens
            customer_data = CustomerSerializer(customer).data
            
            return Response({
                'success': True,
                'message': 'Registration successful',
                'customer': customer_data,
                'tokens': tokens
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CustomerLoginView(APIView):
    """Customer login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Login customer"""
        serializer = CustomerLoginSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            customer = serializer.validated_data['customer']
            
            # Generate tokens
            tokens = CustomerJWTAuthentication.generate_tokens(customer, request)
            
            # Update last activity
            customer.update_last_activity()
            
            # Return customer data with tokens
            customer_data = CustomerSerializer(customer).data
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'customer': customer_data,
                'tokens': tokens
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CustomerLogoutView(APIView):
    """Customer logout endpoint"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Logout customer"""
        try:
            # Get session ID from token payload
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                import jwt
                from django.conf import settings
                
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    session_id = payload.get('session_id')
                    
                    if session_id:
                        CustomerJWTAuthentication.logout_customer(
                            request.user, 
                            session_id
                        )
                    else:
                        CustomerJWTAuthentication.logout_customer(request.user)
                except:
                    # If token decode fails, logout all sessions
                    CustomerJWTAuthentication.logout_customer(request.user)
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            })
            
        except Exception as e:
            logger.error(f"Logout error for customer {request.user.id}: {e}")
            return Response({
                'success': False,
                'error': 'Logout failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerDashboardView(APIView):
    """Customer dashboard data endpoint"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get dashboard data for customer"""
        customer = request.user
        
        try:
            # Get account summary
            account_summary = {
                'account_number': customer.account_number,
                'service_address': customer.property_address,
                'service_type': customer.get_service_type_display(),
                'connection_date': customer.connection_date,
                'account_status': 'Active' if customer.is_active else 'Inactive',
                'meter_number': customer.meter_number,
            }
            
            # Get recent service requests
            from support.models import ServiceRequest
            recent_requests = ServiceRequest.objects.filter(
                customer=customer
            ).order_by('-created_at')[:5]
            
            recent_requests_data = []
            for req in recent_requests:
                recent_requests_data.append({
                    'id': str(req.id),
                    'request_number': req.request_number,
                    'title': req.title,
                    'status': req.status,
                    'issue_type': req.get_issue_type_display(),
                    'created_at': req.created_at,
                    'urgency': req.urgency
                })
            
            # Get service alerts (placeholder)
            service_alerts = []
            
            # Quick actions
            quick_actions = [
                {
                    'title': 'Report an Issue',
                    'description': 'Report water service problems',
                    'icon': 'exclamation-triangle',
                    'url': '/portal/support/new',
                    'primary': True
                },
                {
                    'title': 'View Service Requests',
                    'description': 'Track your service requests',
                    'icon': 'list',
                    'url': '/portal/support',
                    'primary': False
                },
                {
                    'title': 'Update Account',
                    'description': 'Manage your account information',
                    'icon': 'user-cog',
                    'url': '/portal/account',
                    'primary': False
                },
                {
                    'title': 'Contact Support',
                    'description': 'Get help from our team',
                    'icon': 'phone',
                    'url': '/portal/contact',
                    'primary': False
                }
            ]
            
            dashboard_data = {
                'customer': CustomerSerializer(customer).data,
                'account_summary': account_summary,
                'recent_requests': recent_requests_data,
                'service_alerts': service_alerts,
                'quick_actions': quick_actions
            }
            
            return Response({
                'success': True,
                'data': dashboard_data
            })
            
        except Exception as e:
            logger.error(f"Dashboard error for customer {customer.id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to load dashboard data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerProfileView(APIView):
    """Customer profile management endpoint"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get customer profile"""
        customer = request.user
        serializer = CustomerSerializer(customer)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def put(self, request):
        """Update customer profile"""
        customer = request.user
        serializer = CustomerProfileSerializer(
            customer,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated customer data
            customer_data = CustomerSerializer(customer).data
            
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': customer_data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    """Forgot password endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Request password reset"""
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            success = serializer.save()
            
            # Always return success for security
            return Response({
                'success': True,
                'message': 'If an account with this email exists, a password reset link has been sent.'
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    """Reset password endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Reset password with token"""
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            success = serializer.save()
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Password has been reset successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid or expired reset token'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change password endpoint"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Change customer password"""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            customer = serializer.save()
            
            # Generate new tokens
            tokens = CustomerJWTAuthentication.generate_tokens(customer, request)
            
            return Response({
                'success': True,
                'message': 'Password changed successfully',
                'tokens': tokens
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# Additional utility views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_sessions_view(request):
    """Get customer active sessions"""
    customer = request.user
    sessions = CustomerSession.objects.filter(
        customer=customer,
        is_active=True
    ).order_by('-created_at')
    
    sessions_data = []
    for session in sessions:
        sessions_data.append({
            'id': session.id,
            'ip_address': session.ip_address,
            'user_agent': session.user_agent[:100] if session.user_agent else '',
            'created_at': session.created_at,
            'last_used_at': session.last_used_at,
            'expires_at': session.expires_at
        })
    
    return Response({
        'success': True,
        'data': sessions_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_session_view(request, session_id):
    """Logout specific session"""
    customer = request.user
    
    try:
        session = CustomerSession.objects.get(
            id=session_id,
            customer=customer,
            is_active=True
        )
        session.is_active = False
        session.save(update_fields=['is_active'])
        
        return Response({
            'success': True,
            'message': 'Session logged out successfully'
        })
        
    except CustomerSession.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)