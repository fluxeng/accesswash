from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class AssetType(models.Model):
    """Types of infrastructure assets (pipes, valves, meters, etc.)"""
    
    # Predefined asset types
    PIPE = 'pipe'
    VALVE = 'valve'
    METER = 'meter'
    PUMP_STATION = 'pump_station'
    RESERVOIR = 'reservoir'
    TREATMENT_PLANT = 'treatment_plant'
    HYDRANT = 'hydrant'
    
    TYPE_CHOICES = [
        (PIPE, 'Pipe'),
        (VALVE, 'Valve'),
        (METER, 'Water Meter'),
        (PUMP_STATION, 'Pump Station'),
        (RESERVOIR, 'Reservoir'),
        (TREATMENT_PLANT, 'Treatment Plant'),
        (HYDRANT, 'Fire Hydrant'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True, choices=TYPE_CHOICES)
    icon = models.CharField(max_length=50, help_text="Icon name for UI")
    color = models.CharField(max_length=7, default='#3B82F6', help_text="Hex color for map display")
    is_linear = models.BooleanField(default=False, help_text="True for pipes, False for point assets")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'asset_types'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Zone(models.Model):
    """Service zones for organizing infrastructure"""
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    boundary = models.PolygonField(srid=4326, help_text="Zone boundary polygon")
    
    # Zone details
    population = models.IntegerField(null=True, blank=True, help_text="Estimated population served")
    households = models.IntegerField(null=True, blank=True, help_text="Number of households")
    commercial_connections = models.IntegerField(default=0)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'zones'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Asset(models.Model):
    """Base model for all infrastructure assets"""
    
    # Status choices
    OPERATIONAL = 'operational'
    MAINTENANCE = 'maintenance'
    DAMAGED = 'damaged'
    DECOMMISSIONED = 'decommissioned'
    
    STATUS_CHOICES = [
        (OPERATIONAL, 'Operational'),
        (MAINTENANCE, 'Under Maintenance'),
        (DAMAGED, 'Damaged'),
        (DECOMMISSIONED, 'Decommissioned'),
    ]
    
    # Condition ratings
    CONDITION_CHOICES = [
        (5, 'Excellent'),
        (4, 'Good'),
        (3, 'Fair'),
        (2, 'Poor'),
        (1, 'Critical'),
    ]
    
    # Basic info
    asset_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    
    # Location - using PointField for all assets, LineStringField will be in Pipe model
    location = models.PointField(srid=4326, help_text="Asset location point")
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.TextField(blank=True, help_text="Physical address or description")
    
    # Asset details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OPERATIONAL)
    condition = models.IntegerField(choices=CONDITION_CHOICES, default=3)
    installation_date = models.DateField(null=True, blank=True)
    last_inspection = models.DateField(null=True, blank=True)
    next_inspection = models.DateField(null=True, blank=True)
    
    # Technical specifications (JSON for flexibility)
    specifications = models.JSONField(default=dict, blank=True)
    
    # Relationships
    parent_asset = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='child_assets', help_text="For hierarchical assets")
    
    # Metadata
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    notes = models.TextField(blank=True)
    qr_code = models.UUIDField(default=uuid.uuid4, unique=True, help_text="For QR code generation")
    
    # Tracking
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, 
                                 related_name='created_assets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_id']),
            models.Index(fields=['asset_type', 'status']),
            models.Index(fields=['zone']),
        ]
    
    def __str__(self):
        return f"{self.asset_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate asset_id if not provided
        if not self.asset_id:
            prefix = self.asset_type.code.upper()[:3]
            count = Asset.objects.filter(asset_type=self.asset_type).count() + 1
            self.asset_id = f"{prefix}-{count:06d}"
        
        # Auto-assign zone based on location
        if self.location and not self.zone:
            from django.contrib.gis.db.models import Q
            zone = Zone.objects.filter(
                boundary__contains=self.location,
                is_active=True
            ).first()
            if zone:
                self.zone = zone
        
        super().save(*args, **kwargs)


class Pipe(models.Model):
    """Specific model for pipe assets with linear geometry"""
    
    # Material choices
    PVC = 'pvc'
    HDPE = 'hdpe'
    STEEL = 'steel'
    CAST_IRON = 'cast_iron'
    CONCRETE = 'concrete'
    
    MATERIAL_CHOICES = [
        (PVC, 'PVC'),
        (HDPE, 'HDPE'),
        (STEEL, 'Steel'),
        (CAST_IRON, 'Cast Iron'),
        (CONCRETE, 'Concrete'),
    ]
    
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name='pipe_details')
    
    # Pipe geometry
    geometry = models.LineStringField(srid=4326, help_text="Pipe path geometry")
    
    # Pipe specifications
    diameter = models.IntegerField(help_text="Diameter in millimeters", 
                                 validators=[MinValueValidator(10), MaxValueValidator(5000)])
    material = models.CharField(max_length=20, choices=MATERIAL_CHOICES)
    length = models.FloatField(help_text="Length in meters", validators=[MinValueValidator(0)])
    
    # Hydraulic properties
    pressure_rating = models.FloatField(help_text="Maximum pressure in bars", null=True, blank=True)
    flow_rate = models.FloatField(help_text="Design flow rate in liters/second", null=True, blank=True)
    
    # Connections
    start_node = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='outgoing_pipes', help_text="Asset at pipe start")
    end_node = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='incoming_pipes', help_text="Asset at pipe end")
    
    class Meta:
        db_table = 'pipes'
    
    def __str__(self):
        return f"Pipe {self.asset.asset_id} - {self.diameter}mm {self.get_material_display()}"
    
    def save(self, *args, **kwargs):
        # Calculate length from geometry if not provided
        if self.geometry and not self.length:
            # Transform to metric projection for accurate distance
            self.length = self.geometry.transform(3857, clone=True).length
        
        super().save(*args, **kwargs)


class Valve(models.Model):
    """Specific model for valve assets"""
    
    # Valve types
    GATE = 'gate'
    BUTTERFLY = 'butterfly'
    BALL = 'ball'
    CHECK = 'check'
    PRESSURE_REDUCING = 'prv'
    
    VALVE_TYPE_CHOICES = [
        (GATE, 'Gate Valve'),
        (BUTTERFLY, 'Butterfly Valve'),
        (BALL, 'Ball Valve'),
        (CHECK, 'Check Valve'),
        (PRESSURE_REDUCING, 'Pressure Reducing Valve'),
    ]
    
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name='valve_details')
    
    valve_type = models.CharField(max_length=20, choices=VALVE_TYPE_CHOICES)
    diameter = models.IntegerField(help_text="Diameter in millimeters")
    
    # Operational status
    is_open = models.BooleanField(default=True, help_text="Current valve position")
    is_automated = models.BooleanField(default=False, help_text="Remote/automated control")
    turns_to_close = models.IntegerField(null=True, blank=True, help_text="Number of turns to fully close")
    
    # Last operation
    last_operated = models.DateTimeField(null=True, blank=True)
    operated_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'valves'
    
    def __str__(self):
        return f"{self.get_valve_type_display()} - {self.asset.asset_id}"


class Meter(models.Model):
    """Water meter assets"""
    
    # Meter types
    CUSTOMER = 'customer'
    BULK = 'bulk'
    DISTRICT = 'district'
    
    METER_TYPE_CHOICES = [
        (CUSTOMER, 'Customer Meter'),
        (BULK, 'Bulk Meter'),
        (DISTRICT, 'District Meter'),
    ]
    
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name='meter_details')
    
    meter_type = models.CharField(max_length=20, choices=METER_TYPE_CHOICES)
    serial_number = models.CharField(max_length=50, unique=True)
    
    # Meter specifications
    size = models.IntegerField(help_text="Meter size in millimeters")
    brand = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    
    # Reading info
    last_reading = models.FloatField(null=True, blank=True, help_text="Last meter reading in cubic meters")
    last_reading_date = models.DateTimeField(null=True, blank=True)
    
    # Customer linkage (if customer meter)
    customer_account = models.CharField(max_length=50, blank=True, db_index=True)
    
    class Meta:
        db_table = 'meters'
    
    def __str__(self):
        return f"{self.get_meter_type_display()} - {self.serial_number}"


class AssetPhoto(models.Model):
    """Photos of assets for documentation"""
    
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='assets/photos/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    
    # Photo metadata
    taken_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    taken_at = models.DateTimeField(default=timezone.now)
    
    # Location where photo was taken (might differ from asset location)
    photo_location = models.PointField(srid=4326, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'asset_photos'
        ordering = ['-taken_at']
    
    def __str__(self):
        return f"Photo of {self.asset.asset_id} - {self.taken_at}"


class AssetInspection(models.Model):
    """Asset inspection records"""
    
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='inspections')
    
    # Inspection details
    inspection_date = models.DateTimeField(default=timezone.now)
    inspector = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    
    # Findings
    condition_rating = models.IntegerField(choices=Asset.CONDITION_CHOICES)
    notes = models.TextField()
    
    # Issues found
    issues_found = models.JSONField(default=list, blank=True, 
                                  help_text="List of issues found during inspection")
    
    # Next steps
    requires_maintenance = models.BooleanField(default=False)
    maintenance_priority = models.CharField(max_length=20, blank=True, 
                                         choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    
    # Photos
    photos = models.ManyToManyField(AssetPhoto, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'asset_inspections'
        ordering = ['-inspection_date']
    
    def __str__(self):
        return f"Inspection of {self.asset.asset_id} on {self.inspection_date}"
    
    def save(self, *args, **kwargs):
        # Update asset's last inspection date and condition
        if not self.pk:  # New inspection
            self.asset.last_inspection = self.inspection_date.date()
            self.asset.condition = self.condition_rating
            self.asset.save(update_fields=['last_inspection', 'condition'])
        
        super().save(*args, **kwargs)