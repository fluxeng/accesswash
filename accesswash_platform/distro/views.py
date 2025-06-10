from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models import Q
from django.contrib.gis.measure import D
from django.db.models import Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import logging

from .models import (
    AssetType, Zone, Asset, Pipe, Valve, Meter,
    AssetPhoto, AssetInspection
)
from .serializers import (
    AssetTypeSerializer, ZoneSerializer, ZoneGeoSerializer,
    AssetSerializer, AssetCreateSerializer, AssetGeoSerializer,
    PipeGeoSerializer, AssetPhotoSerializer, AssetInspectionSerializer,
    AssetQuickAddSerializer
)
from users.permissions import HasPermission

logger = logging.getLogger(__name__)


class AssetTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for asset types (read-only)"""
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer
    permission_classes = [IsAuthenticated]


class ZoneViewSet(viewsets.ModelViewSet):
    """ViewSet for managing zones"""
    queryset = Zone.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list_geo':
            return ZoneGeoSerializer
        return ZoneSerializer
    
    @action(detail=False, methods=['get'], url_path='geojson')
    def list_geo(self, request):
        """Get zones as GeoJSON"""
        queryset = self.get_queryset()
        serializer = ZoneGeoSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def assets(self, request, pk=None):
        """Get all assets in a zone"""
        zone = self.get_object()
        assets = Asset.objects.filter(zone=zone)
        serializer = AssetSerializer(assets, many=True)
        return Response({
            'zone': zone.name,
            'asset_count': assets.count(),
            'assets': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get zone statistics"""
        zone = self.get_object()
        assets = Asset.objects.filter(zone=zone)
        
        stats = {
            'total_assets': assets.count(),
            'assets_by_type': {},
            'assets_by_status': {},
            'average_condition': assets.aggregate(Avg('condition'))['condition__avg'],
            'assets_needing_inspection': assets.filter(
                next_inspection__lte=timezone.now().date()
            ).count()
        }
        
        # Count by type
        for asset_type in AssetType.objects.all():
            count = assets.filter(asset_type=asset_type).count()
            if count > 0:
                stats['assets_by_type'][asset_type.name] = count
        
        # Count by status
        for status_code, status_name in Asset.STATUS_CHOICES:
            count = assets.filter(status=status_code).count()
            if count > 0:
                stats['assets_by_status'][status_name] = count
        
        return Response(stats)


class AssetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing assets"""
    queryset = Asset.objects.select_related('asset_type', 'zone', 'created_by')
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['asset_id', 'name', 'address', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'name', 'condition']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AssetCreateSerializer
        elif self.action in ['list_geo', 'nearby']:
            return AssetGeoSerializer
        elif self.action == 'quick_add':
            return AssetQuickAddSerializer
        return AssetSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by asset type
        asset_type = self.request.query_params.get('type')
        if asset_type:
            queryset = queryset.filter(asset_type__code=asset_type)
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by condition
        condition = self.request.query_params.get('condition')
        if condition:
            queryset = queryset.filter(condition=condition)
        
        # Filter by zone
        zone = self.request.query_params.get('zone')
        if zone:
            queryset = queryset.filter(zone_id=zone)
        
        # Filter by bounding box (for map view)
        bbox = self.request.query_params.get('bbox')
        if bbox:
            try:
                coords = [float(x) for x in bbox.split(',')]
                if len(coords) == 4:
                    bbox_polygon = Polygon.from_bbox(coords)
                    queryset = queryset.filter(location__within=bbox_polygon)
            except (ValueError, TypeError):
                pass
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='geojson')
    def list_geo(self, request):
        """Get assets as GeoJSON for map display"""
        queryset = self.get_queryset()
        
        # Limit results for performance
        limit = int(request.query_params.get('limit', 1000))
        queryset = queryset[:limit]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'type': 'FeatureCollection',
            'features': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def pipes(self, request):
        """Get all pipes as GeoJSON"""
        pipes = Pipe.objects.select_related('asset', 'asset__zone')
        
        # Apply filters similar to assets
        status = request.query_params.get('status')
        if status:
            pipes = pipes.filter(asset__status=status)
        
        zone = request.query_params.get('zone')
        if zone:
            pipes = pipes.filter(asset__zone_id=zone)
        
        serializer = PipeGeoSerializer(pipes, many=True)
        return Response({
            'type': 'FeatureCollection',
            'features': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Find assets near a point"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = int(request.query_params.get('radius', 100))  # Default 100m
        
        if not lat or not lng:
            return Response({
                'error': 'lat and lng parameters are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            point = Point(float(lng), float(lat), srid=4326)
            nearby_assets = Asset.objects.filter(
                location__distance_lte=(point, D(m=radius))
            ).distance(point).order_by('distance')[:20]
            
            serializer = self.get_serializer(nearby_assets, many=True)
            return Response({
                'center': {'lat': float(lat), 'lng': float(lng)},
                'radius': radius,
                'count': len(serializer.data),
                'assets': serializer.data
            })
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid coordinates'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def quick_add(self, request):
        """Quick asset addition for field workers"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Create asset
        asset = Asset.objects.create(
            name=data['name'],
            asset_type=data['asset_type'],
            location=Point(data['longitude'], data['latitude'], srid=4326),
            notes=data.get('notes', ''),
            created_by=request.user
        )
        
        # Create type-specific details
        if asset.asset_type.code == AssetType.PIPE:
            Pipe.objects.create(
                asset=asset,
                diameter=data.get('diameter', 100),
                material=data.get('material', Pipe.PVC),
                length=0  # To be calculated later
            )
        elif asset.asset_type.code == AssetType.VALVE:
            Valve.objects.create(
                asset=asset,
                valve_type=data.get('valve_type', Valve.GATE),
                diameter=data.get('diameter', 100)
            )
        elif asset.asset_type.code == AssetType.METER:
            Meter.objects.create(
                asset=asset,
                meter_type=Meter.CUSTOMER,
                serial_number=data.get('meter_serial', f'TEMP-{asset.id}'),
                size=15  # Default size
            )
        
        # Handle photo if provided
        if 'photo' in data:
            AssetPhoto.objects.create(
                asset=asset,
                photo=data['photo'],
                caption=f"Quick add photo for {asset.name}",
                taken_by=request.user,
                photo_location=asset.location
            )
        
        return Response(
            AssetSerializer(asset).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def add_photo(self, request, pk=None):
        """Add a photo to an asset"""
        asset = self.get_object()
        serializer = AssetPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        photo = serializer.save(
            asset=asset,
            taken_by=request.user
        )
        
        return Response(
            AssetPhotoSerializer(photo).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def photos(self, request, pk=None):
        """Get all photos for an asset"""
        asset = self.get_object()
        photos = asset.photos.all()
        serializer = AssetPhotoSerializer(photos, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def inspect(self, request, pk=None):
        """Create an inspection for an asset"""
        asset = self.get_object()
        serializer = AssetInspectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        inspection = serializer.save(
            asset=asset,
            inspector=request.user
        )
        
        return Response(
            AssetInspectionSerializer(inspection).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def inspections(self, request, pk=None):
        """Get all inspections for an asset"""
        asset = self.get_object()
        inspections = asset.inspections.all()
        serializer = AssetInspectionSerializer(inspections, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Quick status update"""
        asset = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Asset.STATUS_CHOICES):
            return Response({
                'error': 'Invalid status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        asset.status = new_status
        asset.save(update_fields=['status', 'updated_at'])
        
        return Response({
            'asset_id': asset.asset_id,
            'status': asset.status,
            'updated_at': asset.updated_at
        })
    
    @action(detail=True, methods=['patch'])
    def operate_valve(self, request, pk=None):
        """Record valve operation"""
        asset = self.get_object()
        
        if asset.asset_type.code != AssetType.VALVE:
            return Response({
                'error': 'This operation is only for valves'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        valve = asset.valve_details
        is_open = request.data.get('is_open')
        
        if is_open is None:
            return Response({
                'error': 'is_open field is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        valve.is_open = is_open
        valve.last_operated = timezone.now()
        valve.operated_by = request.user
        valve.save()
        
        return Response({
            'asset_id': asset.asset_id,
            'valve_is_open': valve.is_open,
            'operated_at': valve.last_operated,
            'operated_by': valve.operated_by.get_full_name()
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get asset statistics"""
        assets = self.get_queryset()
        
        stats = {
            'total_assets': assets.count(),
            'assets_by_type': {},
            'assets_by_status': {},
            'assets_by_condition': {},
            'recent_inspections': assets.filter(
                last_inspection__gte=timezone.now().date() - timedelta(days=30)
            ).count(),
            'overdue_inspections': assets.filter(
                next_inspection__lt=timezone.now().date()
            ).count()
        }
        
        # Count by type
        type_counts = assets.values('asset_type__name').annotate(
            count=Count('id')
        )
        for item in type_counts:
            stats['assets_by_type'][item['asset_type__name']] = item['count']
        
        # Count by status
        status_counts = assets.values('status').annotate(count=Count('id'))
        for item in status_counts:
            status_display = dict(Asset.STATUS_CHOICES).get(item['status'])
            stats['assets_by_status'][status_display] = item['count']
        
        # Count by condition
        condition_counts = assets.values('condition').annotate(count=Count('id'))
        for item in condition_counts:
            condition_display = dict(Asset.CONDITION_CHOICES).get(item['condition'])
            stats['assets_by_condition'][condition_display] = item['count']
        
        return Response(stats)


class AssetPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet for managing asset photos"""
    queryset = AssetPhoto.objects.all()
    serializer_class = AssetPhotoSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(taken_by=self.request.user)


class AssetInspectionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing asset inspections"""
    queryset = AssetInspection.objects.select_related('asset', 'inspector')
    serializer_class = AssetInspectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by asset
        asset_id = self.request.query_params.get('asset')
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        
        # Filter by inspector
        inspector_id = self.request.query_params.get('inspector')
        if inspector_id:
            queryset = queryset.filter(inspector_id=inspector_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(inspection_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(inspection_date__lte=end_date)
        
        return queryset.order_by('-inspection_date')
    
    def perform_create(self, serializer):
        serializer.save(inspector=self.request.user)