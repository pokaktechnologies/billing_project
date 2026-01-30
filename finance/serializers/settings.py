from rest_framework import serializers
from ..models import Account, CashflowCategoryMapping, TaxSettings

class CashflowCategoryMappingSerializer(serializers.ModelSerializer):
    class AccountBriefSerializer(serializers.ModelSerializer):
        class Meta:
            model = Account
            fields = ['id', 'name', 'account_number']
    
    accounts = AccountBriefSerializer(many=True, read_only=True)
    account_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Account.objects.all(),
        write_only=True,
        source='accounts'
    )

    class Meta:
        model = CashflowCategoryMapping
        fields = ['id', 'category', 'sub_category', 'accounts', 'account_ids']

    def validate_account_ids(self, accounts):
        """Ensure all selected accounts are posting accounts."""
        for account in accounts:
            if not account.is_posting:
                raise serializers.ValidationError(
                    f"Account '{account.name}' is not a posting account. "
                    "Only posting (Level 3) accounts can be mapped to cashflow categories."
                )
        return accounts

    def create(self, validated_data):
        accounts = validated_data.pop('accounts', [])
        instance = CashflowCategoryMapping.objects.create(**validated_data)
        instance.accounts.set(accounts)
        return instance

    def update(self, instance, validated_data):
        accounts = validated_data.pop('accounts', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if accounts is not None:
            instance.accounts.set(accounts)
        return instance

class CashflowStatementSerializer(serializers.Serializer):
    category = serializers.CharField()
    sub_category = serializers.CharField()
    total_inflow = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_outflow = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_cashflow = serializers.DecimalField(max_digits=12, decimal_places=2)

class TaxSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxSettings
        fields = "__all__"
