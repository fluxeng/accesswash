from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
import logging

from .models import Utility
from .serializers import (
    TenantSerializer, TenantCreateSerializer, TenantDetailSerializer,
    TenantDeleteSerializer, TenantToggleSerializer, DomainCreateSerializer
)
from .utils import (
    soft_delete_tenant, restore_tenant, permanently_delete_tenant,
    toggle_tenant_status, list_tenants, get_tenant_info
)

logger = logging.getLogger('tenants')


class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenants with full CRUD operations
    """
    queryset = Utility.objects.all()
    permission_classes = [IsAuthenticated]  # Uncomment when you add auth
    
    def get_serializer_class(self):
        """Return different serializers for different actions"""
        if self.action == 'create':
            return TenantCreateSerializer
        elif self.action == 'retrieve':
            return TenantDetailSerializer
        elif self.action in ['soft_delete', 'permanent_delete']:
            return TenantDeleteSerializer
        elif self.action == 'toggle_status':
            return TenantToggleSerializer
        return TenantSerializer
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = Utility.objects.all()
        
        # Handle query parameters
        active_only = self.request.query_params.get('active_only', 'false').lower() == 'true'
        include_deleted = self.request.query_params.get('include_deleted', 'false').lower() == 'true'
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create a new tenant"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            tenant = serializer.save()
            response_serializer = TenantSerializer(tenant)
            return Response({
                'success': True,
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.error(f"Validation error in create tenant: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in create tenant: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request, *args, **kwargs):
        """List all tenants with filtering options"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data,
                'count': len(serializer.data)
            })
        except Exception as e:
            logger.error(f"Unexpected error in list tenants: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        """Get detailed tenant information"""
        try:
            tenant = self.get_object()
            info = get_tenant_info(tenant.id)
            
            return Response({
                'success': True,
                'data': info
            })
        except ValidationError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Unexpected error in get tenant info: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], url_path='soft-delete')
    def soft_delete(self, request, pk=None):
        """Soft delete a tenant"""
        tenant = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'tenant': tenant})
        serializer.is_valid(raise_exception=True)
        
        try:
            confirm_name = serializer.validated_data['confirm_name']
            updated_tenant = soft_delete_tenant(tenant.id, confirm_name)
            
            return Response({
                'success': True,
                'message': 'Tenant soft deleted successfully',
                'data': {
                    'utility_id': updated_tenant.id,
                    'name': updated_tenant.name,
                    'is_deleted': updated_tenant.is_deleted,
                    'deleted_on': updated_tenant.deleted_on.isoformat() if updated_tenant.deleted_on else None
                }
            })
        except ValidationError as e:
            logger.error(f"Validation error in soft delete: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in soft delete: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted tenant"""
        try:
            tenant = restore_tenant(pk)
            
            return Response({
                'success': True,
                'message': 'Tenant restored successfully',
                'data': {
                    'utility_id': tenant.id,
                    'name': tenant.name,
                    'is_active': tenant.is_active,
                    'is_deleted': tenant.is_deleted
                }
            })
        except ValidationError as e:
            logger.error(f"Validation error in restore: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in restore: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'], url_path='permanent-delete')
    def permanent_delete(self, request, pk=None):
        """Permanently delete a tenant (only works on soft-deleted tenants)"""
        tenant = get_object_or_404(Utility, pk=pk)
        serializer = self.get_serializer(data=request.data, context={'tenant': tenant})
        serializer.is_valid(raise_exception=True)
        
        try:
            confirm_name = serializer.validated_data['confirm_name']
            success = permanently_delete_tenant(pk, confirm_name)
            
            return Response({
                'success': success,
                'message': 'Tenant permanently deleted successfully'
            })
        except ValidationError as e:
            logger.error(f"Validation error in permanent delete: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in permanent delete: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """Toggle tenant active status"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            is_active = serializer.validated_data.get('is_active')
            tenant = toggle_tenant_status(pk, is_active)
            
            return Response({
                'success': True,
                'data': {
                    'utility_id': tenant.id,
                    'name': tenant.name,
                    'is_active': tenant.is_active
                }
            })
        except ValidationError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in toggle status: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='domains')
    def add_domain(self, request, pk=None):
        """Add a domain to existing tenant"""
        tenant = self.get_object()
        serializer = DomainCreateSerializer(data=request.data, context={'tenant': tenant})
        serializer.is_valid(raise_exception=True)
        
        try:
            domain = serializer.save()
            
            return Response({
                'success': True,
                'data': {
                    'domain': domain.domain,
                    'is_primary': domain.is_primary,
                    'is_active': domain.is_active
                }
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in add domain: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)