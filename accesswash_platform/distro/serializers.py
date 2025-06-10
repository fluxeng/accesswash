from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer, GeometryField
from django.contrib.gis.geos import Point, LineString
from .models import (
    AssetType, Zone, Asset, Pipe, Valve, Meter, 
    AssetPhoto, AssetInspection
)


class AssetTypeSerializer(serializers.ModelSerializer):
    """Serializer for asset types"""
    
    class Meta:
        model = AssetType
        fields = ['id', 'name', 'code', 'icon', 'color', 'is_linear']
        read_only_fields = ['id']


class ZoneSerializer(serializers.ModelSerializer):
    """Basic zone serializer"""
    
    class Meta:
        model = Zone
        fields = [
            'id', 'name', 'code', 'population', 'households',
            'commercial_connections', 'is_active'
        ]
        read_only_fields = ['id']


class ZoneGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for zones"""
    
    class Meta:
        model = Zone
        geo_field = 'boundary'
        fields = [
            'id', 'name', 'code', 'population', 'households',
            'commercial_connections', 'is_active'
        ]


class AssetPhotoSerializer(serializers.ModelSerializer):
    """Serializer for asset photos"""
    taken_by_name = serializers.CharField(source='taken_by.get_full_name', read_only=True)
    
    class Meta:
        model = AssetPhoto
        fields = [
            'id', 'photo', 'caption', 'taken_by', 'taken_by_name',
            'taken_at', 'photo_location', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PipeSerializer(serializers.ModelSerializer):
    """Serializer for pipe details"""
    
    class Meta:
        model = Pipe
        fields = [
            'diameter', 'material', 'length', 'pressure_rating',
            'flow_rate', 'start_node', 'end_node', 'geometry'
        ]


class ValveSerializer(serializers.ModelSerializer):
    """Serializer for valve details"""
    operated_by_name = serializers.CharField(
        source='operated_by.get_full_name', 
        read_only=True
    )
    
    class Meta:
        model = Valve
        fields = [
            'valve_type', 'diameter', 'is_open', 'is_automated',
            'turns_to_close', 'last_operated', 'operated_by',
            'operated_by_name'
        ]


class MeterSerializer(serializers.ModelSerializer):
    """Serializer for meter details"""
    
    class Meta:
        model = Meter
        fields = [
            'meter_type', 'serial_number', 'size', 'brand', 'model',
            'last_reading', 'last_reading_date', 'customer_account'
        ]


class AssetSerializer(serializers.ModelSerializer):
    """Basic asset serializer"""
    asset_type_name = serializers.CharField(source='asset_type.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    # Type-specific details (read-only, populated based on asset type)
    pipe_details = PipeSerializer(read_only=True)
    valve_details = ValveSerializer(read_only=True)
    meter_details = MeterSerializer(read_only=True)
    
    # Counts
    photo_count = serializers.IntegerField(source='photos.count', read_only=True)
    inspection_count = serializers.IntegerField(source='inspections.count', read_only=True)
    
    class Meta:
        model = Asset
        fields = [
            'id', 'asset_id', 'name', 'asset_type', 'asset_type_name',
            'location', 'zone', 'zone_name', 'address', 'status',
            'condition', 'installation_date', 'last_inspection',
            'next_inspection', 'specifications', 'parent_asset',
            'tags', 'notes', 'qr_code', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'pipe_details', 'valve_details',
            'meter_details', 'photo_count', 'inspection_count'
        ]
        read_only_fields = ['id', 'asset_id', 'qr_code', 'created_at', 'updated_at']


class AssetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assets with type-specific details"""
    
    # Type-specific data
    pipe_data = serializers.JSONField(required=False, write_only=True)
    valve_data = serializers.JSONField(required=False, write_only=True)
    meter_data = serializers.JSONField(required=False, write_only=True)
    
    # Allow coordinates input
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    
    class Meta:
        model = Asset
        fields = [
            'name', 'asset_type', 'location', 'latitude', 'longitude',
            'address', 'status', 'condition', 'installation_date',
            'specifications', 'parent_asset', 'tags', 'notes',
            'pipe_data', 'valve_data', 'meter_data'
        ]
    
    def validate(self, data):
        # Convert lat/lng to Point if provided
        if 'latitude' in data and 'longitude' in data:
            data['location'] = Point(data.pop('longitude'), data.pop('latitude'), srid=4326)
        elif not data.get('location'):
            raise serializers.ValidationError("Location is required (either location or lat/lng)")
        
        # Validate type-specific data
        asset_type = data.get('asset_type')
        if asset_type:
            if asset_type.code == AssetType.PIPE and not data.get('pipe_data'):
                raise serializers.ValidationError("Pipe data is required for pipe assets")
            elif asset_type.code == AssetType.VALVE and not data.get('valve_data'):
                raise serializers.ValidationError("Valve data is required for valve assets")
            elif asset_type.code == AssetType.METER and not data.get('meter_data'):
                raise serializers.ValidationError("Meter data is required for meter assets")
        
        return data
    
    def create(self, validated_data):
        # Extract type-specific data
        pipe_data = validated_data.pop('pipe_data', None)
        valve_data = validated_data.pop('valve_data', None)
        meter_data = validated_data.pop('meter_data', None)
        
        # Set created_by
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        
        # Create the asset
        asset = Asset.objects.create(**validated_data)
        
        # Create type-specific details
        if pipe_data and asset.asset_type.code == AssetType.PIPE:
            # Convert geometry coordinates to LineString if needed
            if 'coordinates' in pipe_data:
                coords = pipe_data.pop('coordinates')
                pipe_data['geometry'] = LineString(coords, srid=4326)
            
            Pipe.objects.create(asset=asset, **pipe_data)
            
        elif valve_data and asset.asset_type.code == AssetType.VALVE:
            Valve.objects.create(asset=asset, **valve_data)
            
        elif meter_data and asset.asset_type.code == AssetType.METER:
            Meter.objects.create(asset=asset, **meter_data)
        
        return asset


class AssetGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for assets"""
    asset_type_name = serializers.CharField(source='asset_type.name', read_only=True)
    asset_type_code = serializers.CharField(source='asset_type.code', read_only=True)
    asset_type_icon = serializers.CharField(source='asset_type.icon', read_only=True)
    asset_type_color = serializers.CharField(source='asset_type.color', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    
    class Meta:
        model = Asset
        geo_field = 'location'
        fields = [
            'id', 'asset_id', 'name', 'asset_type_name', 'asset_type_code',
            'asset_type_icon', 'asset_type_color', 'zone_name', 'status',
            'condition', 'last_inspection'
        ]


class PipeGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for pipes"""
    asset_id = serializers.CharField(source='asset.asset_id', read_only=True)
    name = serializers.CharField(source='asset.name', read_only=True)
    status = serializers.CharField(source='asset.status', read_only=True)
    condition = serializers.IntegerField(source='asset.condition', read_only=True)
    zone_name = serializers.CharField(source='asset.zone.name', read_only=True)
    
    class Meta:
        model = Pipe
        geo_field = 'geometry'
        fields = [
            'id', 'asset_id', 'name', 'diameter', 'material',
            'length', 'status', 'condition', 'zone_name'
        ]


class AssetInspectionSerializer(serializers.ModelSerializer):
    """Serializer for asset inspections"""
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    photos = AssetPhotoSerializer(many=True, read_only=True)
    
    class Meta:
        model = AssetInspection
        fields = [
            'id', 'asset', 'asset_name', 'inspection_date', 'inspector',
            'inspector_name', 'condition_rating', 'notes', 'issues_found',
            'requires_maintenance', 'maintenance_priority', 'photos',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['inspector'] = request.user
        
        return super().create(validated_data)


class AssetQuickAddSerializer(serializers.Serializer):
    """Simplified serializer for quick asset addition in field"""
    asset_type = serializers.PrimaryKeyRelatedField(queryset=AssetType.objects.all())
    name = serializers.CharField(max_length=200)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    photo = serializers.ImageField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    # Optional type-specific fields
    diameter = serializers.IntegerField(required=False)  # For pipes/valves
    material = serializers.CharField(required=False)  # For pipes
    valve_type = serializers.CharField(required=False)  # For valves
    meter_serial = serializers.CharField(required=False)  # For meters