from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import logout
from datetime import timedelta
import logging

from .models import User, UserInvitation
from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserProfileSerializer, ChangePasswordSerializer,
    LoginSerializer, UserInvitationSerializer, AcceptInvitationSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, LogoutSerializer
)
from .permissions import IsOwnerOrAdmin, IsSupervisorOrAdmin

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that returns user data with tokens"""
    
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Prepare response data
        user_data = UserSerializer(user).data
        
        return Response({
            'success': True,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'user': user_data
        }, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    """Request password reset"""
    permission_classes = []
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Always return success for security (don't reveal if email exists)
        serializer.save()
        
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


class LogoutView(APIView):
    """Custom logout view"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer
    
    def post(self, request):
        """
        Logout user and blacklist refresh token
        """
        try:
            # Blacklist the refresh token if provided
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Django logout
            logout(request)
            
            return Response({
                'success': True,
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error during logout'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management"""
    queryset = User.objects.filter(is_deleted=False)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'profile':
            return UserProfileSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        return UserSerializer
    
    def get_queryset(self):
        """Filter users based on role and permissions"""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Filter by search query
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(employee_id__icontains=search)
            )
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Role-based filtering
        if not user.is_admin:
            if user.is_supervisor:
                # Supervisors can see all users except admins
                queryset = queryset.exclude(role=User.ADMIN)
            else:
                # Others can only see themselves
                queryset = queryset.filter(id=user.id)
        
        return queryset.order_by('-date_joined')
    
    def create(self, request, *args, **kwargs):
        """Create a new user"""
        # Check permissions
        if not request.user.has_permission('create_user'):
            return Response({
                'success': False,
                'error': 'You do not have permission to create users'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'success': True,
            'data': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update a user"""
        instance = self.get_object()
        
        # Check permissions
        if not (request.user.has_permission('edit_user') or request.user == instance):
            return Response({
                'success': False,
                'error': 'You do not have permission to edit this user'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'success': True,
            'data': UserSerializer(user).data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete a user"""
        instance = self.get_object()
        
        # Check permissions
        if not request.user.has_permission('delete_user'):
            return Response({
                'success': False,
                'error': 'You do not have permission to delete users'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Prevent self-deletion
        if instance == request.user:
            return Response({
                'success': False,
                'error': 'You cannot delete your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        instance.soft_delete()
        
        return Response({
            'success': True,
            'message': 'User deleted successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def profile(self, request):
        """Get or update current user's profile"""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response({
                'success': True,
                'data': serializer.data
            })
        else:
            serializer = self.get_serializer(
                request.user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            return Response({
                'success': True,
                'data': serializer.data
            })
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change current user's password"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Generate new tokens
        refresh = RefreshToken.for_user(request.user)
        
        return Response({
            'success': True,
            'message': 'Password changed successfully',
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
    
    @action(detail=False, methods=['post'])
    def update_location(self, request):
        """Update current user's location (for field techs)"""
        if not request.user.location_tracking_consent:
            return Response({
                'success': False,
                'error': 'Location tracking consent not given'
            }, status=status.HTTP_403_FORBIDDEN)
        
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        
        if not lat or not lng:
            return Response({
                'success': False,
                'error': 'Latitude and longitude are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.update_location(lat, lng)
        
        return Response({
            'success': True,
            'message': 'Location updated successfully'
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a deactivated user"""
        user = self.get_object()
        
        if not request.user.has_permission('edit_user'):
            return Response({
                'success': False,
                'error': 'You do not have permission to activate users'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.is_deleted:
            return Response({
                'success': False,
                'error': 'Cannot activate a deleted user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = True
        user.save(update_fields=['is_active'])
        
        return Response({
            'success': True,
            'message': 'User activated successfully'
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a user"""
        user = self.get_object()
        
        if not request.user.has_permission('edit_user'):
            return Response({
                'success': False,
                'error': 'You do not have permission to deactivate users'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user == request.user:
            return Response({
                'success': False,
                'error': 'You cannot deactivate your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        return Response({
            'success': True,
            'message': 'User deactivated successfully'
        })


class UserInvitationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user invitations"""
    queryset = UserInvitation.objects.all()
    serializer_class = UserInvitationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupervisorOrAdmin]
    
    def get_queryset(self):
        """Filter invitations for current tenant"""
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status == 'pending':
            queryset = queryset.filter(
                is_accepted=False,
                expires_on__gt=timezone.now()
            )
        elif status == 'expired':
            queryset = queryset.filter(
                is_accepted=False,
                expires_on__lte=timezone.now()
            )
        elif status == 'accepted':
            queryset = queryset.filter(is_accepted=True)
        
        return queryset.order_by('-created_on')
    
    @action(detail=False, methods=['post'])
    def accept(self, request):
        """Accept an invitation and create user account"""
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get invitation
        try:
            invitation = UserInvitation.objects.get(
                token=serializer.validated_data['token']
            )
        except UserInvitation.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid invitation token'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if invitation is valid
        if not invitation.is_valid():
            return Response({
                'success': False,
                'error': 'Invitation has expired or already been used'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(email=invitation.email).exists():
            return Response({
                'success': False,
                'error': 'User with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            email=invitation.email,
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            phone_number=serializer.validated_data.get('phone_number', ''),
            role=invitation.role
        )
        
        # Mark invitation as accepted
        invitation.accept()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Account created successfully',
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend invitation email"""
        invitation = self.get_object()
        
        if invitation.is_accepted:
            return Response({
                'success': False,
                'error': 'Invitation has already been accepted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extend expiration
        invitation.expires_on = timezone.now() + timedelta(days=7)
        invitation.save(update_fields=['expires_on'])
        
        # TODO: Resend invitation email
        # send_invitation_email(invitation)
        
        return Response({
            'success': True,
            'message': 'Invitation resent successfully'
        })