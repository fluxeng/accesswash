from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import User, UserInvitation


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    permissions = serializers.ListField(source='get_permissions', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'employee_id', 'first_name', 'last_name',
            'full_name', 'phone_number', 'role', 'avatar',
            'location_tracking_consent', 'last_active', 'is_active',
            'permissions', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'last_active']


class UserDetailSerializer(UserSerializer):
    """Detailed user serializer with additional fields"""
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', 
        read_only=True
    )
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'last_location', 'notification_preferences',
            'is_deleted', 'deleted_on', 'created_by', 'created_by_name'
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    password = serializers.CharField(
        write_only=True, 
        required=False,
        validators=[validate_password]
    )
    send_invitation = serializers.BooleanField(default=True, write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'employee_id', 'first_name', 'last_name',
            'phone_number', 'role', 'password', 'send_invitation'
        ]
    
    def validate_email(self, value):
        """Ensure email is unique within tenant"""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value.lower()
    
    def create(self, validated_data):
        send_invitation = validated_data.pop('send_invitation', True)
        password = validated_data.pop('password', None)
        
        # Create user
        user = User.objects.create_user(
            **validated_data,
            password=password if password else User.objects.make_random_password()
        )
        
        # Set created_by
        request = self.context.get('request')
        if request and request.user:
            user.created_by = request.user
            user.save(update_fields=['created_by'])
        
        # Send invitation if requested and no password provided
        if send_invitation and not password:
            self._create_invitation(user)
        
        return user
    
    def _create_invitation(self, user):
        """Create an invitation for the user"""
        request = self.context.get('request')
        invitation = UserInvitation.objects.create(
            email=user.email,
            role=user.role,
            invited_by=request.user if request else None,
            expires_on=timezone.now() + timedelta(days=7)
        )
        
        # TODO: Send invitation email
        # send_invitation_email(invitation)
        
        return invitation


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating users"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'role',
            'location_tracking_consent', 'notification_preferences',
            'is_active'
        ]
    
    def validate_role(self, value):
        """Prevent users from giving themselves admin role"""
        request = self.context.get('request')
        if request and request.user == self.instance:
            if value == User.ADMIN and self.instance.role != User.ADMIN:
                raise serializers.ValidationError(
                    "You cannot change your own role to admin"
                )
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user's own profile"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'employee_id', 'first_name', 'last_name',
            'phone_number', 'avatar', 'location_tracking_consent',
            'notification_preferences', 'role', 'last_active'
        ]
        read_only_fields = ['id', 'email', 'employee_id', 'role', 'last_active']


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value.lower(), is_active=True, is_deleted=False)
            self.user = user
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            pass
        return value.lower()
    
    def save(self):
        if hasattr(self, 'user'):
            # Generate reset token
            token = default_token_generator.make_token(self.user)
            uid = urlsafe_base64_encode(force_bytes(self.user.pk))
            
            # TODO: Send password reset email with token and uid
            # send_password_reset_email(self.user, token, uid)
            
            return {'uid': uid, 'token': token}
        return None


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    
    def validate(self, data):
        try:
            uid = urlsafe_base64_decode(data['uid']).decode()
            user = User.objects.get(pk=uid, is_active=True, is_deleted=False)
            
            if not default_token_generator.check_token(user, data['token']):
                raise serializers.ValidationError("Invalid or expired reset token")
            
            self.user = user
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid reset link")
        
        return data
    
    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
        return self.user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email = data.get('email').lower()
        password = data.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    "Unable to login with provided credentials"
                )
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
            
            if user.is_deleted:
                raise serializers.ValidationError("User account has been deleted")
            
            # Update last active
            user.update_last_active()
            
        else:
            raise serializers.ValidationError(
                "Must include 'email' and 'password'"
            )
        
        data['user'] = user
        return data


class UserInvitationSerializer(serializers.ModelSerializer):
    """Serializer for user invitations"""
    invited_by_name = serializers.CharField(
        source='invited_by.get_full_name',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserInvitation
        fields = [
            'id', 'email', 'role', 'invited_by', 'invited_by_name',
            'token', 'is_accepted', 'accepted_on', 'expires_on',
            'created_on', 'is_valid'
        ]
        read_only_fields = [
            'id', 'token', 'invited_by', 'is_accepted', 
            'accepted_on', 'created_on'
        ]


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting invitation"""
    token = serializers.UUIDField()
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=17, required=False)


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout request"""
    refresh_token = serializers.CharField(
        required=False, 
        help_text="Refresh token to blacklist (optional)"
    )