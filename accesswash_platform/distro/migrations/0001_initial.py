# Generated by Django 5.1.9 on 2025-07-06 12:33

import django.contrib.gis.db.models.fields
import django.contrib.postgres.fields
import django.core.validators
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_id', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('location', django.contrib.gis.db.models.fields.PointField(help_text='Asset location point', srid=4326)),
                ('address', models.TextField(blank=True, help_text='Physical address or description')),
                ('status', models.CharField(choices=[('operational', 'Operational'), ('maintenance', 'Under Maintenance'), ('damaged', 'Damaged'), ('decommissioned', 'Decommissioned')], default='operational', max_length=20)),
                ('condition', models.IntegerField(choices=[(5, 'Excellent'), (4, 'Good'), (3, 'Fair'), (2, 'Poor'), (1, 'Critical')], default=3)),
                ('installation_date', models.DateField(blank=True, null=True)),
                ('last_inspection', models.DateField(blank=True, null=True)),
                ('next_inspection', models.DateField(blank=True, null=True)),
                ('specifications', models.JSONField(blank=True, default=dict)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), blank=True, default=list, size=None)),
                ('notes', models.TextField(blank=True)),
                ('qr_code', models.UUIDField(default=uuid.uuid4, help_text='For QR code generation', unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'assets',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AssetInspection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inspection_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('condition_rating', models.IntegerField(choices=[(5, 'Excellent'), (4, 'Good'), (3, 'Fair'), (2, 'Poor'), (1, 'Critical')])),
                ('notes', models.TextField()),
                ('issues_found', models.JSONField(blank=True, default=list, help_text='List of issues found during inspection')),
                ('requires_maintenance', models.BooleanField(default=False)),
                ('maintenance_priority', models.CharField(blank=True, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'asset_inspections',
                'ordering': ['-inspection_date'],
            },
        ),
        migrations.CreateModel(
            name='AssetPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('photo', models.ImageField(upload_to='assets/photos/%Y/%m/')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('taken_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('photo_location', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'asset_photos',
                'ordering': ['-taken_at'],
            },
        ),
        migrations.CreateModel(
            name='AssetType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('code', models.CharField(choices=[('pipe', 'Pipe'), ('valve', 'Valve'), ('meter', 'Water Meter'), ('pump_station', 'Pump Station'), ('reservoir', 'Reservoir'), ('treatment_plant', 'Treatment Plant'), ('hydrant', 'Fire Hydrant')], max_length=20, unique=True)),
                ('icon', models.CharField(help_text='Icon name for UI', max_length=50)),
                ('color', models.CharField(default='#3B82F6', help_text='Hex color for map display', max_length=7)),
                ('is_linear', models.BooleanField(default=False, help_text='True for pipes, False for point assets')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'asset_types',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Meter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meter_type', models.CharField(choices=[('customer', 'Customer Meter'), ('bulk', 'Bulk Meter'), ('district', 'District Meter')], max_length=20)),
                ('serial_number', models.CharField(max_length=50, unique=True)),
                ('size', models.IntegerField(help_text='Meter size in millimeters')),
                ('brand', models.CharField(blank=True, max_length=50)),
                ('model', models.CharField(blank=True, max_length=50)),
                ('last_reading', models.FloatField(blank=True, help_text='Last meter reading in cubic meters', null=True)),
                ('last_reading_date', models.DateTimeField(blank=True, null=True)),
                ('customer_account', models.CharField(blank=True, db_index=True, max_length=50)),
            ],
            options={
                'db_table': 'meters',
            },
        ),
        migrations.CreateModel(
            name='Pipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('geometry', django.contrib.gis.db.models.fields.LineStringField(help_text='Pipe path geometry', srid=4326)),
                ('diameter', models.IntegerField(help_text='Diameter in millimeters', validators=[django.core.validators.MinValueValidator(10), django.core.validators.MaxValueValidator(5000)])),
                ('material', models.CharField(choices=[('pvc', 'PVC'), ('hdpe', 'HDPE'), ('steel', 'Steel'), ('cast_iron', 'Cast Iron'), ('concrete', 'Concrete')], max_length=20)),
                ('length', models.FloatField(help_text='Length in meters', validators=[django.core.validators.MinValueValidator(0)])),
                ('pressure_rating', models.FloatField(blank=True, help_text='Maximum pressure in bars', null=True)),
                ('flow_rate', models.FloatField(blank=True, help_text='Design flow rate in liters/second', null=True)),
            ],
            options={
                'db_table': 'pipes',
            },
        ),
        migrations.CreateModel(
            name='Valve',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valve_type', models.CharField(choices=[('gate', 'Gate Valve'), ('butterfly', 'Butterfly Valve'), ('ball', 'Ball Valve'), ('check', 'Check Valve'), ('prv', 'Pressure Reducing Valve')], max_length=20)),
                ('diameter', models.IntegerField(help_text='Diameter in millimeters')),
                ('is_open', models.BooleanField(default=True, help_text='Current valve position')),
                ('is_automated', models.BooleanField(default=False, help_text='Remote/automated control')),
                ('turns_to_close', models.IntegerField(blank=True, help_text='Number of turns to fully close', null=True)),
                ('last_operated', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'valves',
            },
        ),
        migrations.CreateModel(
            name='Zone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('boundary', django.contrib.gis.db.models.fields.PolygonField(help_text='Zone boundary polygon', srid=4326)),
                ('population', models.IntegerField(blank=True, help_text='Estimated population served', null=True)),
                ('households', models.IntegerField(blank=True, help_text='Number of households', null=True)),
                ('commercial_connections', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'zones',
                'ordering': ['name'],
            },
        ),
    ]
