from rest_framework import serializers
from rest_framework_gis.serializers import GeometryField
from django.contrib.gis.geos import Point
from django.utils import timezone
from .models import ServiceRequest, ServiceRequestComment, ServiceRequestPhoto


class ServiceRequestPhotoSerializer(serializers.ModelSerializer):
    """Serializer for service request photos"""
    uploader_name = serializers.SerializerMethodField()
    uploader_type = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequestPhoto
        fields = [
            'id', 'photo', 'photo_url', 'caption', 'file_size', 'image_width',
            'image_height', 'photo_location', 'uploaded_at',
            'uploader_name', 'uploader_type'
        ]
        read_only_fields = [
            'id', 'file_size', 'image_width', 'image_height', 'uploaded_at'
        ]
    
    def get_uploader_name(self, obj):
        return obj.get_uploader_name()
    
    def get_uploader_type(self, obj):
        if obj.uploaded_by_customer:
            return 'customer'
        elif obj.uploaded_by_staff:
            return 'staff'
        return 'unknown'
    
    def get_photo_url(self, obj):
        """Get full URL for photo"""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


class ServiceRequestCommentSerializer(serializers.ModelSerializer):
    """Serializer for service request comments"""
    author_name = serializers.SerializerMethodField()
    author_type = serializers.SerializerMethodField()
    is_from_customer = serializers.SerializerMethodField()
    is_from_staff = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequestComment
        fields = [
            'id', 'comment', 'author_name', 'author_type',
            'is_from_customer', 'is_from_staff',
            'status_changed_from', 'status_changed_to',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_author_name(self, obj):
        return obj.get_author_name()
    
    def get_author_type(self, obj):
        return obj.get_author_type()
    
    def get_is_from_customer(self, obj):
        return obj.author_customer is not None
    
    def get_is_from_staff(self, obj):
        return obj.author_staff is not None


class ServiceRequestSerializer(serializers.ModelSerializer):
    """Basic service request serializer"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    issue_type_display = serializers.CharField(source='get_issue_type_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    resolution_category_display = serializers.CharField(source='get_resolution_category_display', read_only=True)
    
    # Counts
    photos_count = serializers.IntegerField(source='photos.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    
    # Calculated fields
    is_overdue = serializers.SerializerMethodField()
    days_open = serializers.SerializerMethodField()
    can_be_rated = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'request_number', 'customer_name', 'customer_email',
            'assigned_to_name', 'issue_type', 'issue_type_display', 
            'title', 'description', 'urgency', 'urgency_display', 
            'status', 'status_display', 'reported_location', 
            'location_coordinates', 'priority_score', 'resolution_notes', 
            'resolution_category', 'resolution_category_display',
            'customer_rating', 'customer_feedback', 'created_at', 
            'updated_at', 'assigned_at', 'acknowledged_at', 
            'resolved_at', 'closed_at', 'target_response_time', 
            'target_resolution_time', 'actual_response_time',
            'photos_count', 'comments_count', 'is_overdue', 
            'days_open', 'can_be_rated'
        ]
        read_only_fields = [
            'id', 'request_number', 'priority_score', 'created_at',
            'updated_at', 'assigned_at', 'acknowledged_at', 'resolved_at',
            'closed_at', 'target_response_time', 'target_resolution_time',
            'actual_response_time'
        ]
    
    def get_is_overdue(self, obj):
        """Check if request is overdue"""
        if obj.status in ['resolved', 'closed', 'cancelled']:
            return False
        
        if obj.target_resolution_time:
            return timezone.now() > obj.target_resolution_time
        
        return False
    
    def get_days_open(self, obj):
        """Calculate days since request was opened"""
        if obj.closed_at:
            return (obj.closed_at - obj.created_at).days
        else:
            return (timezone.now() - obj.created_at).days
    
    def get_can_be_rated(self, obj):
        """Check if request can be rated by customer"""
        return obj.status in ['resolved', 'closed'] and obj.customer_rating is None


class ServiceRequestDetailSerializer(ServiceRequestSerializer):
    """Detailed service request serializer with related data"""
    photos = ServiceRequestPhotoSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    related_asset_info = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    
    class Meta(ServiceRequestSerializer.Meta):
        fields = ServiceRequestSerializer.Meta.fields + [
            'photos', 'comments', 'related_asset_info', 'timeline'
        ]
    
    def get_comments(self, obj):
        """Get non-internal comments for customers"""
        comments = obj.comments.filter(is_internal=False).order_by('created_at')
        return ServiceRequestCommentSerializer(
            comments, 
            many=True, 
            context=self.context
        ).data
    
    def get_related_asset_info(self, obj):
        """Get related asset information if available"""
        if obj.related_asset:
            return {
                'id': obj.related_asset.id,
                'asset_id': obj.related_asset.asset_id,
                'name': obj.related_asset.name,
                'asset_type': obj.related_asset.asset_type.name,
                'location': {
                    'latitude': obj.related_asset.location.y,
                    'longitude': obj.related_asset.location.x
                } if obj.related_asset.location else None
            }
        return None
    
    def get_timeline(self, obj):
        """Get request timeline/history"""
        timeline = []
        
        # Request created
        timeline.append({
            'event': 'created',
            'title': 'Request Created',
            'description': f'Service request {obj.request_number} was created',
            'timestamp': obj.created_at,
            'actor': obj.customer.get_full_name(),
            'actor_type': 'customer'
        })
        
        # Request acknowledged
        if obj.acknowledged_at:
            timeline.append({
                'event': 'acknowledged',
                'title': 'Request Acknowledged',
                'description': 'Your request has been received and acknowledged',
                'timestamp': obj.acknowledged_at,
                'actor': 'Support Team',
                'actor_type': 'staff'
            })
        
        # Request assigned
        if obj.assigned_at and obj.assigned_to:
            timeline.append({
                'event': 'assigned',
                'title': 'Request Assigned',
                'description': f'Request assigned to {obj.assigned_to.get_full_name()}',
                'timestamp': obj.assigned_at,
                'actor': obj.assigned_to.get_full_name(),
                'actor_type': 'staff'
            })
        
        # Request resolved
        if obj.resolved_at:
            timeline.append({
                'event': 'resolved',
                'title': 'Request Resolved',
                'description': 'Your request has been resolved',
                'timestamp': obj.resolved_at,
                'actor': obj.assigned_to.get_full_name() if obj.assigned_to else 'Support Team',
                'actor_type': 'staff'
            })
        
        # Request closed
        if obj.closed_at:
            timeline.append({
                'event': 'closed',
                'title': 'Request Closed',
                'description': 'Request has been closed',
                'timestamp': obj.closed_at,
                'actor': 'System',
                'actor_type': 'system'
            })
        
        # Add comments to timeline
        for comment in obj.comments.filter(is_internal=False):
            actor_name = comment.get_author_name()
            actor_type = comment.get_author_type()
            
            timeline.append({
                'event': 'comment',
                'title': f'Comment from {actor_name}',
                'description': comment.comment[:100] + '...' if len(comment.comment) > 100 else comment.comment,
                'timestamp': comment.created_at,
                'actor': actor_name,
                'actor_type': actor_type
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        return timeline


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating service requests"""
    # Allow coordinates input
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'issue_type', 'title', 'description', 'urgency',
            'reported_location', 'location_coordinates',
            'latitude', 'longitude'
        ]
    
    def validate_title(self, value):
        """Validate title length and content"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters long.")
        return value.strip()
    
    def validate_description(self, value):
        """Validate description"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long.")
        return value.strip()
    
    def validate_reported_location(self, value):
        """Validate reported location"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Please provide a more detailed location description.")
        return value.strip()
    
    def validate(self, data):
        """Custom validation"""
        # Convert lat/lng to Point if provided
        if 'latitude' in data and 'longitude' in data:
            lat = data.pop('latitude')
            lng = data.pop('longitude')
            
            # Validate coordinate ranges (Kenya approximately)
            if not (-5 <= lat <= 5):
                raise serializers.ValidationError("Latitude must be within Kenya's boundaries.")
            if not (33 <= lng <= 42):
                raise serializers.ValidationError("Longitude must be within Kenya's boundaries.")
            
            data['location_coordinates'] = Point(lng, lat, srid=4326)
        
        return data
    
    def create(self, validated_data):
        # Set customer from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['customer'] = request.user
        
        return super().create(validated_data)


class ServiceRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating service requests (customer side)"""
    
    class Meta:
        model = ServiceRequest
        fields = [
            'title', 'description', 'reported_location',
            'customer_rating', 'customer_feedback'
        ]
    
    def validate_customer_rating(self, value):
        """Validate rating is between 1-5"""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate_customer_feedback(self, value):
        """Validate feedback length"""
        if value and len(value.strip()) > 1000:
            raise serializers.ValidationError("Feedback must be less than 1000 characters.")
        return value.strip() if value else value
    
    def update(self, instance, validated_data):
        # Only allow certain updates based on status
        if instance.status in ['resolved', 'closed', 'cancelled']:
            # Only allow rating and feedback for closed requests
            allowed_fields = ['customer_rating', 'customer_feedback']
            validated_data = {k: v for k, v in validated_data.items() if k in allowed_fields}
        
        return super().update(instance, validated_data)


class ServiceRequestCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments"""
    
    class Meta:
        model = ServiceRequestComment
        fields = ['comment']
    
    def validate_comment(self, value):
        """Validate comment content"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Comment must be at least 3 characters long.")
        if len(value.strip()) > 1000:
            raise serializers.ValidationError("Comment must be less than 1000 characters.")
        return value.strip()
    
    def create(self, validated_data):
        # Set author from request context
        request = self.context.get('request')
        service_request = self.context.get('service_request')
        
        if request and hasattr(request, 'user'):
            validated_data['author_customer'] = request.user
        
        if service_request:
            validated_data['service_request'] = service_request
        
        return super().create(validated_data)


class ServiceRequestPhotoUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading photos"""
    
    class Meta:
        model = ServiceRequestPhoto
        fields = ['photo', 'caption', 'photo_location']
    
    def validate_photo(self, value):
        """Validate photo file"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Photo file size must be less than 10MB.")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError("Only JPEG, PNG, GIF and WebP images are allowed.")
        
        return value
    
    def validate_caption(self, value):
        """Validate caption length"""
        if value and len(value.strip()) > 200:
            raise serializers.ValidationError("Caption must be less than 200 characters.")
        return value.strip() if value else value
    
    def create(self, validated_data):
        # Set uploader from request context
        request = self.context.get('request')
        service_request = self.context.get('service_request')
        
        if request and hasattr(request, 'user'):
            validated_data['uploaded_by_customer'] = request.user
        
        if service_request:
            validated_data['service_request'] = service_request
        
        return super().create(validated_data)


class ServiceRequestRatingSerializer(serializers.Serializer):
    """Serializer for rating service requests"""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(
        max_length=1000, 
        required=False, 
        allow_blank=True,
        help_text="Optional feedback about the service"
    )
    
    def validate_rating(self, value):
        """Validate rating value"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5 stars.")
        return value
    
    def validate_feedback(self, value):
        """Validate feedback"""
        if value and len(value.strip()) > 1000:
            raise serializers.ValidationError("Feedback must be less than 1000 characters.")
        return value.strip() if value else ''


class ServiceRequestQuickCreateSerializer(serializers.Serializer):
    """Simplified serializer for quick issue reporting"""
    issue_type = serializers.ChoiceField(choices=ServiceRequest.ISSUE_TYPES)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=1000)
    urgency = serializers.ChoiceField(
        choices=ServiceRequest.URGENCY_LEVELS, 
        default='standard'
    )
    location = serializers.CharField(max_length=500, help_text="Describe the location of the issue")
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    photo = serializers.ImageField(required=False)
    
    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters long.")
        return value.strip()
    
    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long.")
        return value.strip()
    
    def create(self, validated_data):
        """Create service request with photo if provided"""
        request = self.context.get('request')
        customer = request.user if request else None
        
        if not customer:
            raise serializers.ValidationError("Customer authentication required.")
        
        # Extract photo and location data
        photo = validated_data.pop('photo', None)
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)
        location_text = validated_data.pop('location')
        
        # Create location coordinates if provided
        location_coordinates = None
        if latitude and longitude:
            location_coordinates = Point(longitude, latitude, srid=4326)
        
        # Create service request
        service_request = ServiceRequest.objects.create(
            customer=customer,
            reported_location=location_text,
            location_coordinates=location_coordinates,
            **validated_data
        )
        
        # Add photo if provided
        if photo:
            ServiceRequestPhoto.objects.create(
                service_request=service_request,
                photo=photo,
                caption="Issue photo",
                uploaded_by_customer=customer,
                photo_location=location_coordinates
            )
        
        return service_request


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing service requests"""
    issue_type_display = serializers.CharField(source='get_issue_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_display', read_only=True)
    days_open = serializers.SerializerMethodField()
    has_photos = serializers.SerializerMethodField()
    latest_comment = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'request_number', 'title', 'issue_type', 
            'issue_type_display', 'status', 'status_display',
            'urgency', 'urgency_display', 'created_at', 'updated_at',
            'days_open', 'has_photos', 'latest_comment'
        ]
    
    def get_days_open(self, obj):
        if obj.closed_at:
            return (obj.closed_at - obj.created_at).days
        return (timezone.now() - obj.created_at).days
    
    def get_has_photos(self, obj):
        return obj.photos.exists()
    
    def get_latest_comment(self, obj):
        latest = obj.comments.filter(is_internal=False).order_by('-created_at').first()
        if latest:
            return {
                'comment': latest.comment[:50] + '...' if len(latest.comment) > 50 else latest.comment,
                'author': latest.get_author_name(),
                'created_at': latest.created_at
            }
        return None


class ServiceRequestStatsSerializer(serializers.Serializer):
    """Serializer for service request statistics"""
    total_requests = serializers.IntegerField()
    open_requests = serializers.IntegerField()
    resolved_requests = serializers.IntegerField()
    average_resolution_days = serializers.FloatField()
    most_common_issue = serializers.CharField()
    customer_satisfaction = serializers.FloatField()
    recent_activity = serializers.IntegerField()
    
    # Issue type breakdown
    issue_breakdown = serializers.ListField(
        child=serializers.DictField()
    )
    
    # Monthly trends
    monthly_trends = serializers.ListField(
        child=serializers.DictField()
    )
