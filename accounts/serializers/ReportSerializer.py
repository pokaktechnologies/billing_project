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
from django.db.models import Sum,Avg
from django.db.models.functions import Coalesce
from decimal import Decimal
from finance.utils import round_decimal
from .serializers import *
from .user import *

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

class PurchaseSummaryReportSerializer(serializers.Serializer):
    month = serializers.CharField()
    total_orders = serializers.IntegerField()
    total_suppliers = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)

class SalesSummaryReportSerializer(serializers.Serializer):
    period = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    avg_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_returns = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_sales = serializers.DecimalField(max_digits=12, decimal_places=2)


class SalesSummaryYtdSerializer(serializers.Serializer):
    total_sales_ytd = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_returns_ytd = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_sales_ytd = serializers.DecimalField(max_digits=12, decimal_places=2)


class EmployeeReportSerializer(serializers.ModelSerializer):
    job_detail = JobDetailSerializer(read_only=True)
    # documents = StaffDocumentSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField()
    gender  = serializers.CharField(source='user.gender', read_only=True)
    


    class Meta:
        model = StaffProfile
        fields =[
            'id',
            'name',
            'phone_number',
            'qulification',
            'staff_email',
            'profile_image',
            'gender',
            'date_of_birth',
            'address',
            'job_detail',
            # 'documents'
        ]

    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    

class DepartmentReportSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)
    full_day = serializers.IntegerField(read_only=True)
    part_time = serializers.IntegerField(read_only=True)
    contract = serializers.IntegerField(read_only=True)
    internship = serializers.IntegerField(read_only=True)
    avg_salary = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Department
        fields = [
            'id',
            'name',
            'employee_count',
            'full_day',
            'part_time',
            'contract',
            'internship',
            'avg_salary',
        ]


# product reports
class ProductReportSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(source="id")
    product_name = serializers.CharField(source="name")
    category = serializers.CharField(source="category.name")
    unit = serializers.CharField(source="unit.name")
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock = serializers.IntegerField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "product_id",
            "product_name",
            "category",
            "unit",
            "unit_price",
            "stock",
            "status",
        ]

    def get_status(self, obj):
        if obj.stock == 0:
            return "Out of Stock"
        elif obj.stock <= 200:
            return "Low Stock"
        else:
            return "In Stock"


# product category reports
class ProductCategoryReportSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="name")
    total_products = serializers.SerializerMethodField()
    total_stock_value = serializers.SerializerMethodField()
    avg_price = serializers.SerializerMethodField()
    top_product = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "category",
            "total_products",
            "total_stock_value",
            "avg_price",
            "top_product",
        ]

    def get_products(self, obj):
        return Product.objects.filter(category=obj)

    def get_total_products(self, obj):
        return self.get_products(obj).count()

    def get_total_stock_value(self, obj):

        total = self.get_products(obj).aggregate(
            total_value=Sum(
                ExpressionWrapper(
                    F("stock") * F("unit_price"),
                    output_field=DecimalField()
                )
            )
        )["total_value"]
        return total or 0

    def get_avg_price(self, obj):
        avg = self.get_products(obj).aggregate(
            avg_price=Avg("unit_price")
        )["avg_price"]
        return round(avg, 2) if avg else 0

    def get_top_product(self, obj):
        top = (
            InvoiceItem.objects
            .filter(product__category=obj)
            .values("product__name")
            .annotate(total_sold=Sum("quantity"))
            .order_by("-total_sold")
            .first()
        )
        if top:
            return top["product__name"]
        return "-"


# stock movements reports
class StockMovementReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    product = serializers.CharField()
    transaction_type = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    stock_before = serializers.IntegerField()
    stock_after = serializers.IntegerField()
