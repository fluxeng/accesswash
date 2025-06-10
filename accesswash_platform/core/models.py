from django.db import models


class UtilitySettings(models.Model):
    """Tenant-specific utility settings and branding"""
    utility_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='utility_logos/', null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#2563eb')
    secondary_color = models.CharField(max_length=7, default='#1e40af')
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    
    # Vertical enablement
    distro_enabled = models.BooleanField(default=True)
    huduma_enabled = models.BooleanField(default=False)
    maji_enabled = models.BooleanField(default=False)
    hesabu_enabled = models.BooleanField(default=False)
    ripoti_enabled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_utility_settings'
        verbose_name = 'Utility Settings'
        verbose_name_plural = 'Utility Settings'
    
    def __str__(self):
        return self.utility_name or 'Utility Settings'