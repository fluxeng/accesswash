from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid


class UserManager(BaseUserManager):
    """Custom user manager for tenant-aware user creation"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model for water utility staff"""
    
    # Role choices
    ADMIN = 'admin'
    SUPERVISOR = 'supervisor'
    FIELD_TECH = 'field_tech'
    CUSTOMER_SERVICE = 'customer_service'
    
    ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (SUPERVISOR, 'Supervisor'),
        (FIELD_TECH, 'Field Technician'),
        (CUSTOMER_SERVICE, 'Customer Service'),
    ]
    
    # Override username field with email
    username = None
    email = models.EmailField(unique=True)
    
    # Basic info
    employee_id = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Employee ID for utility staff"
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        help_text="Contact phone number"
    )
    
    # Role and permissions
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=FIELD_TECH,
        help_text="User role in the system"
    )
    
    # Profile
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text="User profile picture"
    )
    
    # Location tracking consent (for field techs)
    location_tracking_consent = models.BooleanField(
        default=False,
        help_text="User consent for GPS location tracking"
    )
    
    # Activity tracking
    last_active = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time user was active in the system"
    )
    
    last_location = models.JSONField(
        null=True,
        blank=True,
        help_text="Last known GPS location {lat, lng, timestamp}"
    )
    
    # Notification preferences
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="User notification preferences"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether user can login"
    )
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    
    deleted_on = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user was soft deleted"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        help_text="User who created this account"
    )
    
    # Use email as username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()

     # Add these to explicitly set related names
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='distro_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='distro_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active', 'is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        # Ensure email is lowercase
        self.email = self.email.lower()
        super().save(*args, **kwargs)
    
    @property
    def is_admin(self):
        return self.role == self.ADMIN or self.is_superuser
    
    @property
    def is_supervisor(self):
        return self.role in [self.ADMIN, self.SUPERVISOR] or self.is_superuser
    
    @property
    def is_field_tech(self):
        return self.role == self.FIELD_TECH
    
    @property
    def is_customer_service(self):
        return self.role == self.CUSTOMER_SERVICE
    
    def get_permissions(self):
        """Get list of permissions based on role"""
        permissions = {
            self.ADMIN: [
                'view_all_users', 'create_user', 'edit_user', 'delete_user',
                'view_all_issues', 'assign_issues', 'close_issues',
                'view_analytics', 'export_data', 'manage_settings'
            ],
            self.SUPERVISOR: [
                'view_team_users', 'create_user', 'edit_user',
                'view_all_issues', 'assign_issues', 'close_issues',
                'view_analytics'
            ],
            self.FIELD_TECH: [
                'view_assigned_issues', 'update_issue_status', 'add_issue_notes',
                'report_new_issue', 'view_assets'
            ],
            self.CUSTOMER_SERVICE: [
                'view_customer_issues', 'create_customer_issue', 
                'update_customer_issue', 'send_notifications'
            ]
        }
        
        return permissions.get(self.role, [])
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        return permission in self.get_permissions()
    
    def update_last_active(self):
        """Update last active timestamp"""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])
    
    def update_location(self, latitude, longitude):
        """Update user's last known location"""
        if self.location_tracking_consent:
            self.last_location = {
                'lat': latitude,
                'lng': longitude,
                'timestamp': timezone.now().isoformat()
            }
            self.save(update_fields=['last_location'])
    
    def soft_delete(self):
        """Soft delete the user"""
        self.is_deleted = True
        self.is_active = False
        self.deleted_on = timezone.now()
        self.save(update_fields=['is_deleted', 'is_active', 'deleted_on'])


class UserInvitation(models.Model):
    """Model for managing user invitations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    
    # Invitation details
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Status
    is_accepted = models.BooleanField(default=False)
    accepted_on = models.DateTimeField(null=True, blank=True)
    expires_on = models.DateTimeField()
    
    # Metadata
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_invitations'
        ordering = ['-created_on']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['token']),
            models.Index(fields=['is_accepted', 'expires_on']),
        ]
    
    def __str__(self):
        return f"Invitation for {self.email} as {self.get_role_display()}"
    
    def is_valid(self):
        """Check if invitation is still valid"""
        return (
            not self.is_accepted and 
            self.expires_on > timezone.now()
        )
    
    def accept(self):
        """Mark invitation as accepted"""
        self.is_accepted = True
        self.accepted_on = timezone.now()
        self.save(update_fields=['is_accepted', 'accepted_on'])