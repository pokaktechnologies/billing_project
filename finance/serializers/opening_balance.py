from rest_framework import serializers

from ..models import (
    Account,
    AccountOpeningBalance,
    FinancialYear,
)
from ..services.opening_balance import (
    update_opening_balances,
)
from django.db import transaction
class OpeningBalanceDashboardSerializer(serializers.ModelSerializer):
    opening_balance = serializers.SerializerMethodField()
    class Meta:
        model = Account

        fields = [
            "id",
            "account_number",
            "name",
            "type",
            "opening_balance",
        ]

    def get_opening_balance(self, obj):
        financial_year = self.context.get("financial_year")

        if not financial_year:
            return "0.00"

        balance = (
            AccountOpeningBalance.objects.filter(
                account=obj,
                financial_year=financial_year
            )
            .first()
        )

        if balance:
            return balance.opening_balance

        return "0.00"


class OpeningBalanceRowSerializer(serializers.Serializer):
    account = serializers.IntegerField()
    opening_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    def validate_account(self, value):

        if not Account.objects.filter(
            id=value,
            is_posting=True,
            status="active"
        ).exists():
            raise serializers.ValidationError(
                "Invalid account."
            )

        return value


class OpeningBalanceBulkUpdateSerializer(serializers.Serializer):

    financial_year = serializers.IntegerField()
    balances = OpeningBalanceRowSerializer(many=True)

    def validate_financial_year(self, value):

        if not FinancialYear.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Invalid Financial Year."
            )
        return value
    
    def save(self):

        update_opening_balances(
            financial_year_id=self.validated_data["financial_year"],
            balances=self.validated_data["balances"]
        )

        return True

class FinancialYearSerializer(serializers.ModelSerializer):

    class Meta:
        model = FinancialYear
        fields = [
            "id",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "status",
            "remarks",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]