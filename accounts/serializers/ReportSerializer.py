from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import *
import random
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.utils import timezone
from attendance.models import DailyAttendance, AttendanceSession
from accounts.models import CustomUser
from datetime import datetime
from django.utils import timezone

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from datetime import datetime
from attendance.models import DailyAttendance, AttendanceSession

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from datetime import datetime, time as dt_time
from attendance.models import DailyAttendance, AttendanceSession
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from decimal import Decimal
from finance.utils import round_decimal
from .serializers import *

# Invoice Report
class InvoiceReportSerializer(serializers.ModelSerializer):

    client_name = serializers.SerializerMethodField()
    intern_name = serializers.SerializerMethodField()
    pending_amount = serializers.SerializerMethodField()
    effective_tax_rate = serializers.SerializerMethodField()
    tax_rate = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    total_amount_without_tax = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceModel
        fields = [
            "id",
            "invoice_type",
            "invoice_number",
            "invoice_date",
            "invoice_grand_total",
            "client_name",
            "intern_name",
            "pending_amount",
            "effective_tax_rate",
            "tax_rate",
            "tax_amount",
            "total_amount_without_tax",
            "created_at",
        ]

    def get_client_name(self, obj):
        if obj.client:
            return f"{obj.client.first_name} {obj.client.last_name}"
        return None

    def get_intern_name(self, obj):
        if obj.intern:
            return f"{obj.intern.user.first_name} {obj.intern.user.last_name}"
        return None

    def get_pending_amount(self, obj):
        receipt = ReceiptModel.objects.filter(invoice=obj).aggregate(
            total=Coalesce(Sum("cheque_amount"), Decimal("0.00"))
        )
        total_received = receipt["total"]
        return round_decimal(obj.invoice_grand_total - total_received)

    def get_tax_amount(self, obj):
        return round_decimal(obj.total_tax)

    def get_total_amount_without_tax(self, obj):
        return round_decimal(obj.total_without_tax)

    def get_tax_rate(self, obj):
        if obj.total_without_tax > 0:
            return round_decimal(
                (obj.total_tax / obj.total_without_tax) * Decimal("100")
            )
        return Decimal("0.00")

    def get_effective_tax_rate(self, obj):
        if obj.total_without_tax > 0:
            return round_decimal(
                (obj.total_tax / obj.total_without_tax) * Decimal("100")
            )
        return Decimal("0.00")
    
# Purchase Order Report
class PurchaseOrderReportSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    terms_and_conditions_id = serializers.IntegerField(source='terms_and_conditions.id', read_only=True)
    terms_and_conditions_title = serializers.CharField(source='terms_and_conditions.title', read_only=True)
    termsandconditions = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "supplier_name",
            "supplier",
            "purchase_order_number",
            "purchase_order_date",
            "contact_person_name",
            "contact_person_number",
            "quotation_number",
            "grand_total",
            "remark",
            "terms_and_conditions_id",
            "terms_and_conditions_title",
            "termsandconditions"
        ]

    def get_supplier_name(self, obj):
        return f"{obj.supplier.first_name} {obj.supplier.last_name}"
    
    def get_termsandconditions(self, obj):
        if obj.terms_and_conditions:
            points = obj.terms_and_conditions.termsandconditionspoint_set.all()  # Assuming the related_name is 'points'
            return TermsAndConditionsPointSerializer(points, many=True).data
        return []
    
    
# Material Receive Report

class MaterialReceiveReportSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    purchase_order_number = serializers.CharField(
        source='purchase_order.purchase_order_number',
        read_only=True
    )
    items = MaterialReceiveItemSerializer(many=True, read_only=True)

    class Meta:
        model = MaterialReceive
        fields = [
            'id',
            'material_receive_number',
            'received_date',
            'supplier',
            'supplier_name',
            'purchase_order',
            'purchase_order_number',
            'grand_total',
            'remark',
            'items'
        ]

    def get_supplier_name(self, obj):
        return f"{obj.supplier.first_name} {obj.supplier.last_name}"

