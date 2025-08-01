from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from .models import Customer, CustomerVerification
from .authentication import CustomerAuthenticationBackend, CustomerJWTAuthentication, CustomerPasswordResetService
import logging

logger = logging.getLogger(__name__)


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for customer registration"""
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = Customer
        fields = [
            'email', 'phone_number', 'password', 'password_confirm',
            'first_name', 'last_name', 'property_address',
            'account_number', 'meter_number', 'language'
        ]
        extra_kwargs = {
            'account_number': {'required': False},
            'meter_number': {'required': False},
        }
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if Customer.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A customer with this email already exists.")
        return value.lower()
    
    def validate_phone_number(self, value):
        """Validate phone number if provided"""
        if value and Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A customer with this phone number already exists.")
        return value
    
    def validate(self, data):
        """Validate password confirmation"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return data
    
    def create(self, validated_data):
        """Create new customer"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        customer = Customer.objects.create(**validated_data)
        customer.set_password(password)
        customer.save()
        
        # Send welcome email
        try:
            from core.email_service import email_service
            context = {
                'customer': customer,
                'email_subject': f'Welcome to {customer._state.db or "Water Services"} Customer Portal'
            }
            
            email_service.send_email(
                template_name='portal/welcome',
                context=context,
                to_emails=[customer.email]
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {customer.email}: {e}")
        
        return customer


class CustomerLoginSerializer(serializers.Serializer):
    """Serializer for customer login"""
    username = serializers.CharField(help_text="Email or phone number")
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        """Authenticate customer"""
        backend = CustomerAuthenticationBackend()
        customer = backend.authenticate(
            request=self.context.get('request'),
            username=data['username'],
            password=data['password']
        )
        
        if not customer:
            raise serializers.ValidationError("Invalid credentials.")
        
        data['customer'] = customer
        return data


class CustomerSerializer(serializers.ModelSerializer):
    """Basic customer serializer"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'full_name', 'account_number', 'meter_number', 'property_address',
            'service_type', 'language', 'email_verified', 'phone_verified',
            'last_login', 'created_at'
        ]
        read_only_fields = [
            'id', 'account_number', 'email_verified', 'phone_verified',
            'last_login', 'created_at'
        ]


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for customer profile updates"""
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'phone_number', 'property_address',
            'language', 'notification_preferences'
        ]
    
    def validate_phone_number(self, value):
        """Validate phone number uniqueness"""
        if value:
            existing = Customer.objects.filter(phone_number=value).exclude(
                id=self.instance.id if self.instance else None
            )
            if existing.exists():
                raise serializers.ValidationError("This phone number is already in use.")
        return value


class CustomerDashboardSerializer(serializers.Serializer):
    """Serializer for dashboard data"""
    customer = CustomerSerializer(read_only=True)
    account_summary = serializers.JSONField(read_only=True)
    recent_requests = serializers.JSONField(read_only=True)
    service_alerts = serializers.JSONField(read_only=True)
    quick_actions = serializers.JSONField(read_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        return value.lower()
    
    def save(self):
        """Send password reset email"""
        email = self.validated_data['email']
        return CustomerPasswordResetService.request_password_reset(email)


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset"""
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        """Validate password confirmation"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return data
    
    def save(self):
        """Reset password using token"""
        token = self.validated_data['token']
        new_password = self.validated_data['new_password']
        return CustomerPasswordResetService.reset_password(token, new_password)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    current_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_current_password(self, value):
        """Validate current password"""
        customer = self.context['request'].user
        if not customer.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, data):
        """Validate password confirmation"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("New passwords do not match.")
        return data
    
    def save(self):
        """Change password"""
        customer = self.context['request'].user
        new_password = self.validated_data['new_password']
        
        customer.set_password(new_password)
        customer.save(update_fields=['password_hash'])
        
        # Invalidate all existing sessions except current
        # (Implementation would need session tracking)
        
        return customer