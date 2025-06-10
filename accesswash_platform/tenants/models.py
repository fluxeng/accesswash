from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Utility(TenantMixin):
    """
    Water utility tenant model - each utility is a separate tenant
    """
    name = models.CharField(max_length=100, help_text="Utility company name")
    is_active = models.BooleanField(default=True, help_text="Whether utility account is active")
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag")
    deleted_on = models.DateTimeField(null=True, blank=True, help_text="When utility was soft deleted")
    
    # Timestamps
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Water Utility"
        verbose_name_plural = "Water Utilities"
    
    def __str__(self):
        deleted_indicator = " (DELETED)" if self.is_deleted else ""
        return f"{self.name}{deleted_indicator}"


class Domain(DomainMixin):
    """
    Domain model for tenant access - each utility can have multiple domains
    """
    is_active = models.BooleanField(default=True, help_text="Whether domain is active")
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Utility Domain"
        verbose_name_plural = "Utility Domains"
    
    def __str__(self):
        primary_indicator = " (Primary)" if self.is_primary else ""
        return f"{self.domain}{primary_indicator}"