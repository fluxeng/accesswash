from rest_framework import serializers
from .models import Utility, Domain 


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['domain', 'is_primary', 'is_active']


class TenantCreateSerializer(serializers.ModelSerializer):
    domain = serializers.CharField(write_only=True)
    
    class Meta:
        model = Utility
        fields = ['name', 'domain']
    
    def create(self, validated_data):
        domain_name = validated_data.pop('domain')
        
        # Import here to avoid circular imports
        from .utils import create_tenant
        
        utility, domain = create_tenant(validated_data['name'], domain_name)
        return utility


class TenantSerializer(serializers.ModelSerializer):
    domains = DomainSerializer(many=True, read_only=True)
    
    class Meta:
        model = Utility
        fields = [
            'id', 'name', 'schema_name', 'is_active', 'is_deleted',
            'deleted_on', 'created_on', 'domains'
        ]
        read_only_fields = ['id', 'schema_name', 'deleted_on', 'created_on']


class TenantDetailSerializer(TenantSerializer):
    """Extended serializer with more details for single tenant view"""
    
    class Meta(TenantSerializer.Meta):
        fields = TenantSerializer.Meta.fields + []  # Add any additional fields you want


class TenantDeleteSerializer(serializers.Serializer):
    confirm_name = serializers.CharField(required=True)
    
    def validate_confirm_name(self, value):
        tenant = self.context.get('tenant')
        if tenant and value != tenant.name:
            raise serializers.ValidationError("Confirmation name doesn't match tenant name")
        return value


class TenantToggleSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)


class DomainCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['domain', 'is_primary']
    
    def create(self, validated_data):
        # Get tenant from context
        tenant = self.context['tenant']
        
        from .utils import add_domain_to_tenant
        
        domain = add_domain_to_tenant(
            tenant.id,
            validated_data['domain'],
            validated_data.get('is_primary', False)
        )
        return domain