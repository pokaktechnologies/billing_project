from rest_framework import serializers
from ..models import Account


class AccountSerializer(serializers.ModelSerializer):
    """
    Serializer for Account model with hierarchy and posting validation.
    """
    depth = serializers.SerializerMethodField(read_only=True)
    parent_account_name = serializers.CharField(source='parent_account.name', read_only=True)
    parent_account_number = serializers.CharField(source='parent_account.account_number', read_only=True)
    
    class Meta: 
        model = Account
        fields = [
            'id',
            'account_number',
            'name',
            'type',
            'parent_account',
            'parent_account_name',
            'parent_account_number',
            'is_posting',
            'opening_balance',
            'closing_balance',
            'status',
            'depth',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'closing_balance', 'depth']
    
    def get_depth(self, obj):
        """Return the hierarchy depth of this account."""
        return obj.get_depth()
    
    def validate(self, data):
        """
        Validate account data using model-level validation.
        This ensures errors are surfaced properly in API responses.
        """
        # Create a temporary instance to run model validation
        instance = self.instance
        account = Account(
            id=instance.id if instance else None,
            account_number=data.get('account_number', instance.account_number if instance else None),
            name=data.get('name', instance.name if instance else ''),
            type=data.get('type', instance.type if instance else ''),
            parent_account=data.get('parent_account', instance.parent_account if instance else None),
            is_posting=data.get('is_posting', instance.is_posting if instance else True),
            opening_balance=data.get('opening_balance', instance.opening_balance if instance else 0),
            status=data.get('status', instance.status if instance else 'active'),
        )
        
        # Run model validation
        try:
            account.clean()
        except Exception as e:
            if hasattr(e, 'message_dict'):
                raise serializers.ValidationError(e.message_dict)
            raise serializers.ValidationError(str(e))
        
        return data
