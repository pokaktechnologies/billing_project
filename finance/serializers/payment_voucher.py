from rest_framework import serializers

from ..services.payment_voucher import process_payment_voucher_creation, process_payment_voucher_update
from ..models import PaymentVoucher

class PaymentVoucherSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentVoucher
        fields = [
            "id",
            "voucher_number",
            "date",
            "payment_method",
            "pay_to",
            "debit_account",
            "credit_account",
            "amount",
            "reference_number",
            "remarks",
            "status",
            "journal_entry",
            "salesperson",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ('id', 'voucher_number', 'created_at', 'updated_at', 'journal_entry', 'user')

    
    def validate(self, attrs):

        if attrs["amount"] <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero."})
        
        if attrs["debit_account"] == attrs["credit_account"]:
            raise serializers.ValidationError({"account": "Debit and Credit accounts must be different."})
        
        return attrs
    
    def create(self, validated_data):

        user = self.context["request"].user

        return process_payment_voucher_creation(
            validated_data,
            user
        )

    def update(self, instance, validated_data):

        return process_payment_voucher_update(
            instance,
            validated_data
        )
    
