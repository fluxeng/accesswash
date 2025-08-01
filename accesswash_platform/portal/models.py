from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import RegexValidator
from django.utils import timezone
from django.contrib.gis.db import models as gis_models
import uuid
import secrets


class Customer(models.Model):
    """Customer model for portal users (separate from utility staff)"""
    
    # Basic identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True, help_text="Primary email address")
    
    # Phone number with validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        null=True,
        db_index=True,
        help_text="Alternative login method"
    )
    
    # Authentication
    password_hash = models.CharField(max_length=128, help_text="Hashed password") 
    
    # Personal information
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    
    # Account details
    account_number = models.CharField(max_length=50, unique=True, db_index=True)
    meter_number = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    
    # Link to existing distro system
    meter = models.ForeignKey(
        'distro.Meter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        help_text="Linked water meter"
    )
    
    # Address information
    property_address = models.TextField(help_text="Service address")
    property_location = gis_models.PointField(srid=4326, null=True, blank=True)
    
    # Service details
    connection_date = models.DateField(null=True, blank=True)
    service_type = models.CharField(
        max_length=20,
        choices=[
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
            ('industrial', 'Industrial'),
            ('institutional', 'Institutional'),
        ],
        default='residential'
    )
    
    # Preferences
    language = models.CharField(max_length=10, default='en', choices=[
        ('en', 'English'),
        ('sw', 'Swahili'),
    ])
    
    notification_preferences = models.JSONField(default=dict, blank=True, help_text="Communication preferences")
    
    # Status fields
    is_active = models.BooleanField(default=True, help_text="Can login to portal")
    email_verified = models.BooleanField(default=False, help_text="Email address verified")
    phone_verified = models.BooleanField(default=False, help_text="Phone number verified")
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag")
    
    # Activity tracking
    last_login = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['account_number']),
            models.Index(fields=['meter_number']),
            models.Index(fields=['is_active', 'is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.account_number})"
    
    def get_full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def set_password(self, raw_password):
        """Set password with Django's password hashing"""
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check password against hash"""
        return check_password(raw_password, self.password_hash)
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def get_default_notification_preferences(self):
        """Get default notification preferences"""
        return {
            'email_service_updates': True,
            'email_billing': True,
            'email_emergency': True,
            'sms_service_updates': False,
            'sms_billing': False,
            'sms_emergency': True,
            'push_notifications': True,
        }
    
    def save(self, *args, **kwargs):
        # Auto-generate account number if not provided
        if not self.account_number:
            # Generate account number: ACC + timestamp + random
            timestamp = timezone.now().strftime('%Y%m')
            random_suffix = secrets.token_hex(3).upper()
            self.account_number = f"ACC{timestamp}{random_suffix}"
        
        # Set default notification preferences
        if not self.notification_preferences:
            self.notification_preferences = self.get_default_notification_preferences()
        
        # Ensure email is lowercase
        if self.email:
            self.email = self.email.lower()
        
        super().save(*args, **kwargs)


class CustomerSession(models.Model):
    """Customer session management for JWT tokens"""
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True, db_index=True)
    refresh_token = models.CharField(max_length=255, unique=True, db_index=True)
    
    # Session details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    
    # Session status
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_token']),
            models.Index(fields=['refresh_token']),
            models.Index(fields=['customer', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Session for {self.customer.email} - {self.created_at}"
    
    def is_valid(self):
        """Check if session is still valid"""
        return self.is_active and self.expires_at > timezone.now()
    
    def extend_session(self, hours=24):
        """Extend session expiration"""
        self.expires_at = timezone.now() + timezone.timedelta(hours=hours)
        self.save(update_fields=['expires_at', 'last_used_at'])


class CustomerVerification(models.Model):
    """Email and phone verification for customers"""
    
    VERIFICATION_TYPES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('password_reset', 'Password Reset'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='verifications')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    token = models.CharField(max_length=32, unique=True, db_index=True)
    
    # Verification details
    email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=17, null=True, blank=True)
    
    # Status
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'customer_verifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['customer', 'verification_type']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_verification_type_display()} for {self.customer.email}"
    
    def is_valid(self):
        """Check if verification token is still valid"""
        return not self.is_used and self.expires_at > timezone.now()
    
    def use_token(self):
        """Mark token as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    def save(self, *args, **kwargs):
        # Generate token if not provided
        if not self.token:
            self.token = secrets.token_urlsafe(24)
        
        super().save(*args, **kwargs)