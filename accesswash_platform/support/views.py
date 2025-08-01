from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
import logging

from .models import ServiceRequest, ServiceRequestComment, ServiceRequestPhoto
from .serializers import (
    ServiceRequestSerializer, ServiceRequestDetailSerializer,
    ServiceRequestCreateSerializer, ServiceRequestUpdateSerializer,
    ServiceRequestCommentSerializer, ServiceRequestCommentCreateSerializer,
    ServiceRequestPhotoSerializer, ServiceRequestPhotoUploadSerializer
)
from portal.permissions import IsCustomer

logger = logging.getLogger(__name__)


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for customer service requests"""
    permission_classes = [IsAuthenticated, IsCustomer]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['request_number', 'title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'urgency', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter requests for current customer"""
        customer = self.request.user
        queryset = ServiceRequest.objects.filter(customer=customer)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by issue type
        issue_type = self.request.query_params.get('issue_type')
        if issue_type:
            queryset = queryset.filter(issue_type=issue_type)
        
        # Filter by urgency
        urgency = self.request.query_params.get('urgency')
        if urgency:
            queryset = queryset.filter(urgency=urgency)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.select_related('customer', 'assigned_to', 'related_asset')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ServiceRequestUpdateSerializer
        elif self.action == 'retrieve':
            return ServiceRequestDetailSerializer
        return ServiceRequestSerializer
    
    def create(self, request, *args, **kwargs):
        """Create new service request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service_request = serializer.save()
        
        # Send notification to utility staff
        try:
            self._notify_staff_new_request(service_request)
        except Exception as e:
            logger.warning(f"Failed to notify staff about new request {service_request.request_number}: {e}")
        
        # Return detailed view
        response_serializer = ServiceRequestDetailSerializer(service_request)
        
        return Response({
            'success': True,
            'message': 'Service request created successfully',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update service request"""
        instance = self.get_object()
        
        # Only allow updates if request is not closed
        if instance.status in ['resolved', 'closed', 'cancelled']:
            return Response({
                'success': False,
                'error': 'Cannot update a closed service request'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Service request updated successfully',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add comment to service request"""
        service_request = self.get_object()
        
        serializer = ServiceRequestCommentCreateSerializer(
            data=request.data,
            context={
                'request': request,
                'service_request': service_request
            }
        )
        
        if serializer.is_valid():
            comment = serializer.save()
            
            # Notify staff about new customer comment
            try:
                self._notify_staff_new_comment(service_request, comment)
            except Exception as e:
                logger.warning(f"Failed to notify staff about new comment: {e}")
            
            response_serializer = ServiceRequestCommentSerializer(comment)
            
            return Response({
                'success': True,
                'message': 'Comment added successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_photo(self, request, pk=None):
        """Upload photo to service request"""
        service_request = self.get_object()
        
        serializer = ServiceRequestPhotoUploadSerializer(
            data=request.data,
            context={
                'request': request,
                'service_request': service_request
            }
        )
        
        if serializer.is_valid():
            photo = serializer.save()
            
            response_serializer = ServiceRequestPhotoSerializer(photo)
            
            return Response({
                'success': True,
                'message': 'Photo uploaded successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get all comments for service request"""
        service_request = self.get_object()
        
        # Only show non-internal comments to customers
        comments = service_request.comments.filter(
            is_internal=False
        ).order_by('created_at')
        
        serializer = ServiceRequestCommentSerializer(comments, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def photos(self, request, pk=None):
        """Get all photos for service request"""
        service_request = self.get_object()
        photos = service_request.photos.all().order_by('uploaded_at')
        
        serializer = ServiceRequestPhotoSerializer(photos, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate completed service request"""
        service_request = self.get_object()
        
        if service_request.status not in ['resolved', 'closed']:
            return Response({
                'success': False,
                'error': 'Can only rate resolved or closed requests'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        rating = request.data.get('rating')
        feedback = request.data.get('feedback', '')
        
        if not rating or not (1 <= int(rating) <= 5):
            return Response({
                'success': False,
                'error': 'Rating must be between 1 and 5'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service_request.customer_rating = int(rating)
        service_request.customer_feedback = feedback
        service_request.save(update_fields=['customer_rating', 'customer_feedback'])
        
        return Response({
            'success': True,
            'message': 'Rating submitted successfully'
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get customer's service request statistics"""
        customer = request.user
        
        # Basic counts
        total_requests = ServiceRequest.objects.filter(customer=customer).count()
        open_requests = ServiceRequest.objects.filter(
            customer=customer,
            status__in=['open', 'acknowledged', 'assigned', 'in_progress']
        ).count()
        resolved_requests = ServiceRequest.objects.filter(
            customer=customer,
            status__in=['resolved', 'closed']
        ).count()
        
        # By issue type
        issue_type_stats = ServiceRequest.objects.filter(
            customer=customer
        ).values('issue_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Recent activity
        recent_updates = ServiceRequest.objects.filter(
            customer=customer,
            updated_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        stats = {
            'total_requests': total_requests,
            'open_requests': open_requests,
            'resolved_requests': resolved_requests,
            'recent_updates': recent_updates,
            'issue_type_breakdown': list(issue_type_stats),
            'average_rating': None  # Could calculate if needed
        }
        
        return Response({
            'success': True,
            'data': stats
        })
    
    def _notify_staff_new_request(self, service_request):
        """Send notification to staff about new service request"""
        from core.email_service import email_service
        
        # Get utility staff emails (supervisors and admins)
        from users.models import User
        staff_emails = User.objects.filter(
            role__in=[User.ADMIN, User.SUPERVISOR],
            is_active=True,
            is_deleted=False
        ).values_list('email', flat=True)
        
        if staff_emails:
            context = {
                'service_request': service_request,
                'customer': service_request.customer,
                'email_subject': f'New Service Request: {service_request.request_number}'
            }
            
            email_service.send_email(
                template_name='support/new_request_staff',
                context=context,
                to_emails=list(staff_emails)
            )
    
    def _notify_staff_new_comment(self, service_request, comment):
        """Send notification to assigned staff about new customer comment"""
        if service_request.assigned_to:
            from core.email_service import email_service
            
            context = {
                'service_request': service_request,
                'comment': comment,
                'customer': service_request.customer,
                'email_subject': f'New Comment on {service_request.request_number}'
            }
            
            email_service.send_email(
                template_name='support/new_comment_staff',
                context=context,
                to_emails=[service_request.assigned_to.email]
            )


class ServiceRequestCommentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for service request comments (read-only for customers)"""
    serializer_class = ServiceRequestCommentSerializer
    permission_classes = [IsAuthenticated, IsCustomer]
    
    def get_queryset(self):
        """Get comments for customer's service requests only"""
        customer = self.request.user
        return ServiceRequestComment.objects.filter(
            service_request__customer=customer,
            is_internal=False  # Hide internal staff comments
        ).order_by('-created_at')


class ServiceRequestPhotoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for service request photos (read-only for customers)"""
    serializer_class = ServiceRequestPhotoSerializer
    permission_classes = [IsAuthenticated, IsCustomer]
    
    def get_queryset(self):
        """Get photos for customer's service requests only"""
        customer = self.request.user
        return ServiceRequestPhoto.objects.filter(
            service_request__customer=customer
        ).order_by('-uploaded_at')