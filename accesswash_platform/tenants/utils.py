import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django_tenants.utils import schema_context
from .models import Utility, Domain

# Configure logging
logger = logging.getLogger('tenants')


def create_tenant(name, domain_name, is_primary=True):
    """
    Create a new tenant (utility) with domain
    
    Args:
        name (str): Utility name
        domain_name (str): Domain for the utility (e.g., 'nairobi.distro.app')
        is_primary (bool): Whether this is the primary domain
    
    Returns:
        tuple: (utility, domain) objects
        
    Raises:
        ValidationError: If tenant creation fails
    """
    logger.info(f"Starting tenant creation for: {name} with domain: {domain_name}")
    
    try:
        with transaction.atomic():
            # Create the utility (tenant)
            utility = Utility.objects.create(
                schema_name=_generate_schema_name(name),
                name=name,
                is_active=True
            )
            logger.info(f"Created utility: {utility.name} with schema: {utility.schema_name}")
            
            # Create the domain
            domain = Domain.objects.create(
                domain=domain_name,
                tenant=utility,
                is_primary=is_primary,
                is_active=True
            )
            logger.info(f"Created domain: {domain.domain} for utility: {utility.name}")
            
            # Create the tenant schema
            utility.create_schema(check_if_exists=True)
            logger.info(f"Created schema for utility: {utility.name}")
            
            # Run migrations on the new schema
            with schema_context(utility.schema_name):
                from django.core.management import call_command
                call_command('migrate_schemas', '--schema', utility.schema_name, verbosity=0)
                logger.info(f"Ran migrations for schema: {utility.schema_name}")
            
            logger.info(f"Successfully created tenant: {utility.name}")
            return utility, domain
            
    except Exception as e:
        logger.error(f"Failed to create tenant {name}: {str(e)}")
        raise ValidationError(f"Failed to create tenant: {str(e)}")


def soft_delete_tenant(utility_id, confirm_name=None):
    """
    Soft delete a tenant (mark as deleted, deactivate, but keep data)
    
    Args:
        utility_id (int): ID of the utility to delete
        confirm_name (str): Utility name for confirmation (safety check)
    
    Returns:
        Utility: The soft-deleted utility object
        
    Raises:
        ValidationError: If deletion fails or confirmation doesn't match
    """
    try:
        utility = Utility.objects.get(id=utility_id)
        
        # Safety check - require name confirmation
        if confirm_name and confirm_name != utility.name:
            raise ValidationError("Utility name confirmation doesn't match")
        
        if utility.is_deleted:
            raise ValidationError("Utility is already deleted")
        
        logger.warning(f"Soft deleting tenant: {utility.name} (ID: {utility_id})")
        
        from django.utils import timezone
        utility.is_deleted = True
        utility.is_active = False
        utility.deleted_on = timezone.now()
        utility.save(update_fields=['is_deleted', 'is_active', 'deleted_on'])
        
        # Also deactivate all domains
        utility.domains.update(is_active=False)
        
        logger.warning(f"Soft deleted utility: {utility.name}")
        return utility
        
    except Utility.DoesNotExist:
        logger.error(f"Utility with ID {utility_id} not found")
        raise ValidationError("Utility not found")
    except Exception as e:
        logger.error(f"Failed to soft delete tenant {utility_id}: {str(e)}")
        raise ValidationError(f"Failed to soft delete tenant: {str(e)}")


def restore_tenant(utility_id):
    """
    Restore a soft-deleted tenant
    
    Args:
        utility_id (int): ID of the utility to restore
    
    Returns:
        Utility: The restored utility object
        
    Raises:
        ValidationError: If restoration fails
    """
    try:
        utility = Utility.objects.get(id=utility_id)
        
        if not utility.is_deleted:
            raise ValidationError("Utility is not deleted")
        
        logger.info(f"Restoring tenant: {utility.name} (ID: {utility_id})")
        
        utility.is_deleted = False
        utility.is_active = True
        utility.deleted_on = None
        utility.save(update_fields=['is_deleted', 'is_active', 'deleted_on'])
        
        # Reactivate primary domain
        primary_domain = utility.domains.filter(is_primary=True).first()
        if primary_domain:
            primary_domain.is_active = True
            primary_domain.save(update_fields=['is_active'])
        
        logger.info(f"Restored utility: {utility.name}")
        return utility
        
    except Utility.DoesNotExist:
        logger.error(f"Utility with ID {utility_id} not found")
        raise ValidationError("Utility not found")
    except Exception as e:
        logger.error(f"Failed to restore tenant {utility_id}: {str(e)}")
        raise ValidationError(f"Failed to restore tenant: {str(e)}")


def permanently_delete_tenant(utility_id, confirm_name=None):
    """
    Permanently delete a tenant and all its data (only works on soft-deleted tenants)
    
    Args:
        utility_id (int): ID of the utility to delete
        confirm_name (str): Utility name for confirmation (safety check)
    
    Returns:
        bool: True if deleted successfully
        
    Raises:
        ValidationError: If deletion fails or confirmation doesn't match
    """
    try:
        utility = Utility.objects.get(id=utility_id)
        
        # Safety check - require name confirmation
        if confirm_name and confirm_name != utility.name:
            raise ValidationError("Utility name confirmation doesn't match")
        
        # Only allow permanent deletion of soft-deleted tenants
        if not utility.is_deleted:
            raise ValidationError("Can only permanently delete soft-deleted utilities. Soft delete first.")
        
        logger.warning(f"PERMANENTLY deleting tenant: {utility.name} (ID: {utility_id})")
        
        with transaction.atomic():
            # Delete the schema and all data
            utility.delete_schema()
            logger.info(f"Deleted schema for utility: {utility.name}")
            
            # Delete the utility record (domains will cascade)
            utility_name = utility.name
            utility.delete()
            logger.warning(f"PERMANENTLY deleted utility: {utility_name}")
            
            return True
            
    except Utility.DoesNotExist:
        logger.error(f"Utility with ID {utility_id} not found")
        raise ValidationError("Utility not found")
    except Exception as e:
        logger.error(f"Failed to permanently delete tenant {utility_id}: {str(e)}")
        raise ValidationError(f"Failed to permanently delete tenant: {str(e)}")


def delete_tenant(utility_id, confirm_name=None):
    """
    Soft delete a tenant (wrapper for backward compatibility)
    """
    return soft_delete_tenant(utility_id, confirm_name)


def add_domain_to_tenant(utility_id, domain_name, is_primary=False):
    """
    Add a new domain to an existing tenant
    
    Args:
        utility_id (int): ID of the utility
        domain_name (str): New domain name
        is_primary (bool): Whether this should be the primary domain
    
    Returns:
        Domain: The created domain object
    """
    try:
        utility = Utility.objects.get(id=utility_id)
        logger.info(f"Adding domain {domain_name} to utility: {utility.name}")
        
        # If this is set as primary, make others non-primary
        if is_primary:
            Domain.objects.filter(tenant=utility, is_primary=True).update(is_primary=False)
            logger.info(f"Updated existing primary domains for utility: {utility.name}")
        
        domain = Domain.objects.create(
            domain=domain_name,
            tenant=utility,
            is_primary=is_primary,
            is_active=True
        )
        
        logger.info(f"Successfully added domain {domain_name} to utility: {utility.name}")
        return domain
        
    except Utility.DoesNotExist:
        logger.error(f"Utility with ID {utility_id} not found")
        raise ValidationError("Utility not found")
    except Exception as e:
        logger.error(f"Failed to add domain {domain_name} to utility {utility_id}: {str(e)}")
        raise ValidationError(f"Failed to add domain: {str(e)}")


def toggle_tenant_status(utility_id, is_active=None):
    """
    Activate or deactivate a tenant
    
    Args:
        utility_id (int): ID of the utility
        is_active (bool): New status, or None to toggle current status
    
    Returns:
        Utility: Updated utility object
    """
    try:
        utility = Utility.objects.get(id=utility_id)
        
        if is_active is None:
            is_active = not utility.is_active
        
        utility.is_active = is_active
        utility.save(update_fields=['is_active'])
        
        status = "activated" if is_active else "deactivated"
        logger.info(f"Utility {utility.name} has been {status}")
        
        return utility
        
    except Utility.DoesNotExist:
        logger.error(f"Utility with ID {utility_id} not found")
        raise ValidationError("Utility not found")


def list_tenants(active_only=False, include_deleted=False):
    """
    List all tenants with their domains
    
    Args:
        active_only (bool): Only return active tenants
        include_deleted (bool): Include soft-deleted tenants in results
    
    Returns:
        QuerySet: Utilities with prefetched domains
    """
    queryset = Utility.objects.prefetch_related('domains').order_by('name')
    
    if not include_deleted:
        queryset = queryset.filter(is_deleted=False)
    
    if active_only:
        queryset = queryset.filter(is_active=True)
    
    logger.info(f"Retrieved {queryset.count()} tenants (active_only={active_only}, include_deleted={include_deleted})")
    return queryset


def get_tenant_info(utility_id):
    """
    Get detailed information about a tenant
    
    Args:
        utility_id (int): ID of the utility
    
    Returns:
        dict: Tenant information
    """
    try:
        utility = Utility.objects.prefetch_related('domains').get(id=utility_id)
        
        info = {
            'id': utility.id,
            'name': utility.name,
            'schema_name': utility.schema_name,
            'is_active': utility.is_active,
            'is_deleted': utility.is_deleted,
            'deleted_on': utility.deleted_on.isoformat() if utility.deleted_on else None,
            'created_on': utility.created_on,
            'updated_on': utility.updated_on,
            'domains': [
                {
                    'domain': domain.domain,
                    'is_primary': domain.is_primary,
                    'is_active': domain.is_active,
                    'created_on': domain.created_on
                }
                for domain in utility.domains.all()
            ]
        }
        
        logger.info(f"Retrieved info for tenant: {utility.name}")
        return info
        
    except Utility.DoesNotExist:
        logger.error(f"Utility with ID {utility_id} not found")
        raise ValidationError("Utility not found")


def _generate_schema_name(name):
    """
    Generate a valid PostgreSQL schema name from utility name
    
    Args:
        name (str): Utility name
    
    Returns:
        str: Valid schema name
    """
    import re
    # Convert to lowercase, replace spaces with underscores, remove special chars
    schema_name = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
    
    # Ensure it starts with a letter
    if not schema_name[0].isalpha():
        schema_name = f"tenant_{schema_name}"
    
    # Ensure uniqueness by checking existing schemas
    base_name = schema_name
    counter = 1
    while Utility.objects.filter(schema_name=schema_name).exists():
        schema_name = f"{base_name}_{counter}"
        counter += 1
    
    return schema_name


# Context manager for working within a tenant schema
class tenant_context:
    """
    Context manager to execute code within a specific tenant's schema
    
    Usage:
        with tenant_context('tenant_schema_name'):
            # Your code here runs in the tenant's schema
            users = User.objects.all()
    """
    def __init__(self, schema_name):
        self.schema_name = schema_name
    
    def __enter__(self):
        from django_tenants.utils import schema_context
        self._context = schema_context(self.schema_name)
        return self._context.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._context.__exit__(exc_type, exc_val, exc_tb)