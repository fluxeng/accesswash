from django.db import models
from django.utils import timezone
from django.contrib.gis.db import models as gis_models
import uuid


class ServiceRequest(models.Model):
    """Customer service requests and issue reports"""
    
    # Issue type choices
    ISSUE_TYPES = [
        ('no_water', 'No Water Supply'),
        ('low_pressure', 'Low Water Pressure'),
        ('pipe_burst', 'Pipe Burst/Leak'),
        ('water_quality', 'Water Quality Issue'),
        ('meter_problem', 'Meter Problem'),
        ('billing_inquiry', 'Billing Inquiry'),
        ('connection_request', 'New Connection Request'),
        ('disconnection', 'Service Disconnection'),
        ('other', 'Other Issue'),
    ]
    
    # Urgency levels
    URGENCY_LEVELS = [
        ('emergency', 'Emergency'),
        ('high', 'High'),
        ('standard', 'Standard'),
        ('low', 'Low'),
    ]
    
    # Status choices
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('acknowledged', 'Acknowledged'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Customer and assignment
    customer = models.ForeignKey('portal.Customer', on_delete=models.CASCADE, related_name='service_requests')
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests',
        help_text="Staff member assigned to this request"
    )
    
    # Issue details
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    title = models.CharField(max_length=200, help_text="Brief description of the issue")
    description = models.TextField(help_text="Detailed description of the issue")
    urgency = models.CharField(max_length=10, choices=URGENCY_LEVELS, default='standard')
    
    # Location information
    reported_location = models.TextField(help_text="Address or description of issue location")
    location_coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    
    # Asset relationship
    related_asset = models.ForeignKey(
        'distro.Asset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_requests',
        help_text="Related infrastructure asset"
    )
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority_score = models.IntegerField(default=0, help_text="System-calculated priority score")
    
    # Resolution
    resolution_notes = models.TextField(blank=True)
    resolution_category = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('resolved_field', 'Resolved in Field'),
            ('resolved_phone', 'Resolved over Phone'),
            ('resolved_office', 'Resolved in Office'),
            ('duplicate', 'Duplicate Request'),
            ('invalid', 'Invalid Request'),
            ('referred', 'Referred to Other Department'),
        ]
    )
    
    # Customer feedback
    customer_rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="Customer satisfaction rating (1-5 stars)"
    )
    customer_feedback = models.TextField(blank=True)
    
    # Work order integration
    created_work_order = models.BooleanField(default=False)
    work_order_number = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # SLA tracking
    target_response_time = models.DateTimeField(null=True, blank=True)
    target_resolution_time = models.DateTimeField(null=True, blank=True)
    actual_response_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'service_requests'
        verbose_name = 'Service Request'
        verbose_name_plural = 'Service Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['issue_type', 'urgency']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.request_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Auto-generate request number
        if not self.request_number:
            year = timezone.now().year
            # Count existing requests this year
            count = ServiceRequest.objects.filter(
                request_number__startswith=f'SR-{year}'
            ).count() + 1
            self.request_number = f'SR-{year}-{count:05d}'
        
        # Calculate priority score
        self.priority_score = self._calculate_priority_score()
        
        # Set SLA times based on urgency (only if not already set)
        if not self.target_response_time:
            # Use current time if created_at is not set yet
            base_time = self.created_at if self.created_at else timezone.now()
            self.target_response_time = self._calculate_target_response_time(base_time)
        
        if not self.target_resolution_time:
            # Use current time if created_at is not set yet
            base_time = self.created_at if self.created_at else timezone.now()
            self.target_resolution_time = self._calculate_target_resolution_time(base_time)
        
        super().save(*args, **kwargs)
    
    def _calculate_priority_score(self):
        """Calculate priority score based on urgency and issue type"""
        urgency_weights = {
            'emergency': 100,
            'high': 75,
            'standard': 50,
            'low': 25,
        }
        
        issue_weights = {
            'no_water': 30,
            'pipe_burst': 25,
            'low_pressure': 20,
            'water_quality': 20,
            'meter_problem': 15,
            'billing_inquiry': 10,
            'connection_request': 15,
            'disconnection': 10,
            'other': 10,
        }
        
        urgency_score = urgency_weights.get(self.urgency, 50)
        issue_score = issue_weights.get(self.issue_type, 10)
        
        return urgency_score + issue_score
    
    def _calculate_target_response_time(self, base_time=None):
        """Calculate target response time based on urgency"""
        from datetime import timedelta
        
        if base_time is None:
            base_time = self.created_at if self.created_at else timezone.now()
        
        response_times = {
            'emergency': timedelta(hours=1),
            'high': timedelta(hours=4),
            'standard': timedelta(hours=24),
            'low': timedelta(hours=72),
        }
        
        return base_time + response_times.get(self.urgency, timedelta(hours=24))
    
    def _calculate_target_resolution_time(self, base_time=None):
        """Calculate target resolution time based on urgency"""
        from datetime import timedelta
        
        if base_time is None:
            base_time = self.created_at if self.created_at else timezone.now()
        
        resolution_times = {
            'emergency': timedelta(hours=4),
            'high': timedelta(hours=24),
            'standard': timedelta(days=3),
            'low': timedelta(days=7),
        }
        
        return base_time + resolution_times.get(self.urgency, timedelta(days=3))
    
    def assign_to_staff(self, user):
        """Assign request to staff member"""
        self.assigned_to = user
        self.assigned_at = timezone.now()
        self.status = 'assigned'
        self.save(update_fields=['assigned_to', 'assigned_at', 'status', 'updated_at'])
    
    def acknowledge(self):
        """Mark request as acknowledged"""
        if self.status == 'open':
            self.status = 'acknowledged'
            self.acknowledged_at = timezone.now()
            self.actual_response_time = self.acknowledged_at
            self.save(update_fields=['status', 'acknowledged_at', 'actual_response_time', 'updated_at'])
    
    def resolve(self, resolution_notes='', resolution_category=''):
        """Mark request as resolved"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        if resolution_notes:
            self.resolution_notes = resolution_notes
        if resolution_category:
            self.resolution_category = resolution_category
        self.save(update_fields=[
            'status', 'resolved_at', 'resolution_notes', 
            'resolution_category', 'updated_at'
        ])
    
    def close(self):
        """Close the request"""
        self.status = 'closed'
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])


class ServiceRequestComment(models.Model):
    """Comments and updates on service requests"""
    
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    # Author (either customer or staff)
    author_customer = models.ForeignKey(
        'portal.Customer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='service_comments'
    )
    author_staff = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='service_comments'
    )
    
    # Comment content
    comment = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal staff notes, hidden from customer"
    )
    
    # Status change tracking
    status_changed_from = models.CharField(max_length=20, blank=True)
    status_changed_to = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_request_comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['service_request', 'created_at']),
            models.Index(fields=['author_customer']),
            models.Index(fields=['author_staff']),
        ]
    
    def __str__(self):
        author = self.get_author_name()
        return f"Comment by {author} on {self.service_request.request_number}"
    
    def get_author_name(self):
        """Get the name of the comment author"""
        if self.author_customer:
            return self.author_customer.get_full_name()
        elif self.author_staff:
            return self.author_staff.get_full_name()
        return "Unknown"
    
    def get_author_type(self):
        """Get the type of author (customer or staff)"""
        if self.author_customer:
            return 'customer'
        elif self.author_staff:
            return 'staff'
        return 'unknown'


class ServiceRequestPhoto(models.Model):
    """Photos attached to service requests"""
    
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    
    # Photo details
    photo = models.ImageField(upload_to='service_requests/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    
    # Upload details
    uploaded_by_customer = models.ForeignKey(
        'portal.Customer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='uploaded_photos'
    )
    uploaded_by_staff = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='uploaded_photos'
    )
    
    # Photo metadata
    file_size = models.IntegerField(null=True, blank=True, help_text="File size in bytes")
    image_width = models.IntegerField(null=True, blank=True)
    image_height = models.IntegerField(null=True, blank=True)
    
    # Location where photo was taken
    photo_location = gis_models.PointField(srid=4326, null=True, blank=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'service_request_photos'
        ordering = ['uploaded_at']
        indexes = [
            models.Index(fields=['service_request', 'uploaded_at']),
        ]
    
    def __str__(self):
        return f"Photo for {self.service_request.request_number} - {self.uploaded_at}"
    
    def get_uploader_name(self):
        """Get the name of the photo uploader"""
        if self.uploaded_by_customer:
            return self.uploaded_by_customer.get_full_name()
        elif self.uploaded_by_staff:
            return self.uploaded_by_staff.get_full_name()
        return "Unknown"