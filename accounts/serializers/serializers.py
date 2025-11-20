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

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        # Prevent superusers from obtaining tokens via this endpoint
        if getattr(user, 'is_superuser', False):
            raise serializers.ValidationError({
                "detail": "Superuser login via this token endpoint is not allowed."
            })
        now = timezone.localtime()
        current_time = now.time()

        # Define sessions with thresholds
        sessions = {
            "session1": {"start": dt_time(9, 0), "end": dt_time(12, 0), "late_threshold": dt_time(9, 15)},
            "session2": {"start": dt_time(12, 0), "end": dt_time(15, 0), "late_threshold": dt_time(12, 15)},
            "session3": {"start": dt_time(15, 0), "end": dt_time(18, 0), "late_threshold": dt_time(15, 15)},
        }

        session_name = None
        login_time = None
        session_status = None

        if hasattr(user, "staff_profile"):
            # --- Morning session special rules ---
            if current_time < dt_time(8, 0):
                # Before 8:00 AM → just allow login, no attendance recorded
                print(f"{user.email} logged in before 8:00 AM. No attendance recorded yet.")
                return data
            elif dt_time(8, 0) <= current_time < dt_time(9, 0):
                # Clamp to 9:00 AM
                session_name = "session1"
                login_time = timezone.make_aware(datetime.combine(now.date(), dt_time(9, 0)))
                session_status = "present"
            elif dt_time(9, 0) <= current_time < dt_time(12, 0):
                # After 9:00 AM → normal late calculation
                session_name = "session1"
                login_time = timezone.make_aware(datetime.combine(now.date(), current_time))
                session_status = "present" if current_time <= sessions["session1"]["late_threshold"] else "late"
            # --- Afternoon & Evening sessions ---
            elif dt_time(12, 0) <= current_time < dt_time(15, 0):
                session_name = "session2"
                login_time = timezone.make_aware(datetime.combine(now.date(), current_time))
                session_status = "present" if current_time <= sessions["session2"]["late_threshold"] else "late"
            elif dt_time(15, 0) <= current_time < dt_time(18, 0):
                session_name = "session3"
                login_time = timezone.make_aware(datetime.combine(now.date(), current_time))
                session_status = "present" if current_time <= sessions["session3"]["late_threshold"] else "late"

            # Update attendance
            if session_name:
                try:
                    daily_attendance = DailyAttendance.objects.get(
                        staff=user.staff_profile,
                        date=now.date()
                    )
                    attendance_session, created = AttendanceSession.objects.get_or_create(
                        daily_attendance=daily_attendance,
                        session=session_name,
                        defaults={"login_time": login_time, "status": session_status}
                    )
                    if not created and not attendance_session.login_time:
                        attendance_session.login_time = login_time
                        attendance_session.status = session_status
                        attendance_session.save()
                    print(f"{user.email} | {session_name} login at {login_time}, status: {session_status}")
                except DailyAttendance.DoesNotExist:
                    print(f"No daily attendance for {user.email} today")
        else:
            print(f"Skipping attendance update for {user.email} (not staff)")

        return data

# Custom serializer for superuser token obtain (allows only superusers)
class CustomSuperuserTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        # Allow only superusers to obtain tokens via this endpoint
        if not getattr(user, 'is_superuser', False):
            raise serializers.ValidationError({
                "detail": "Only superuser may obtain token from this endpoint."
            })
        return data

# Serializer for user registration
class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

# Serializer for OTP verification
class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)



class GettingStartedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email','organization_name', 'business_location', 'state_province']    
        read_only_fields = ['email']
        
class QuotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quotation
        fields = '__all__'
        


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'
        

class HelpLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpLink
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class UserSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSetting
        fields = '__all__'

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'        
        

class PrintTermsAndConditionsSerializer(serializers.ModelSerializer):
    termsandconditions = serializers.CharField(source='terms_and_conditions.title', read_only=True)

    class Meta:
        model = TermsAndConditionsPoint
        fields = '__all__'

    



            
class DeliveryOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOrder
        fields = [
            'id',
            'customer_name',
            'delivery_number',
            'delivery_date',
            'delivery_amount',
            'delivery_location',
            'received_location',
            'salesperson',
            'terms',
            'due_date',
            'subject',
            'attachments',
            'quantity'
        ]
        read_only_fields = ['delivery_number']        
        
# class SupplierPurchaseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SupplierPurchase
#         fields = [
#                 'id', 'supplier_name', 'purchase_number', 'date', 'amount', 'terms', 
#                 'due_date', 'purchase_person', 'subject', 'add_stock', 'attachments','quantity'
#             ]
#         read_only_fields = ['supplier_number']        
        

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class SupplierDetailSerializer(serializers.ModelSerializer):
    termsandconditions_title = serializers.CharField(source='payment_terms.title', read_only=True)
    termsandconditions = serializers.SerializerMethodField()
    class Meta:
        model = Supplier
        fields = '__all__' 

    def get_termsandconditions(self, obj):
        # Get related TermsAndConditions
        terms = obj.payment_terms
        # Get points related to this TermsAndConditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data  

        
class DeliveryChallanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryChallan
        fields = '__all__'
        
# class ProductSerializer(serializers.ModelSerializer):
#     unit = serializers.CharField()  #
#     category=serializers.CharField()
#     salesperson = SalesPersonSerializer(read_only=True)

    
    
#     class Meta:
#         model = Product
#         fields = ['id','name', 'product_description', 'unit', 'unit_price', 'category','sgst','cgst','SalesPerson',]
        

#     def validate_unit(self, value):
#         """Fetch and return the Unit instance based on its name."""
#         try:
#             return Unit.objects.get(name=value)
#         except Unit.DoesNotExist:
#             raise serializers.ValidationError(f"Unit '{value}' does not exist.")

#     def validate_category(self, value):
#         """Fetch and return the Category instance based on its name or ID."""
#         try:
#             # You can modify this logic based on your input (name or ID)
#             if value.isdigit():  # Check if it's an ID
#                 return Category.objects.get(id=value)
#             else:  # Otherwise, assume it's a category name
#                 return Category.objects.get(name=value)
#         except Category.DoesNotExist:
#             raise serializers.ValidationError(f"Category '{value}' does not exist.")

#     def create(self, validated_data):
#         """Override create method to handle unit and category assignment."""
#         unit_instance = validated_data.pop('unit')  # `unit` is already validated as a Unit instance
#         category_instance = validated_data.pop('category')  # `category` is also validated as a Category instance

#         validated_data['unit'] = unit_instance
#         validated_data['category'] = category_instance

#         return Product.objects.create(**validated_data)

    # def update(self, instance, validated_data):
    #     """Override update method to handle unit and category assignment."""
    #     unit_instance = validated_data.pop('unit', None)
    #     category_instance = validated_data.pop('category', None)

    #     if unit_instance:
    #         instance.unit = unit_instance  # Assign Unit instance
    #     if category_instance:
    #         instance.category = category_instance  # Assign Category instance

    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()
    #     return instance
    
    
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        
 

class SalesPersonSerializer(serializers.ModelSerializer):
    assigned_staff_email = serializers.CharField(source='assigned_staff.staff_email', read_only=True)
    class Meta:
        model = SalesPerson
        fields = '__all__'
        read_only_fields = []        

      
        
class QuotationOrderSerializer(serializers.ModelSerializer):
    quotation_date_display = serializers.SerializerMethodField()
    client_firstname = serializers.CharField(source='client.first_name', read_only=True)
    client_lastname = serializers.CharField(source='client.last_name', read_only=True)
    lead_number = serializers.CharField(source='lead.lead_number', read_only=True)
    lead_date = serializers.DateTimeField(source='lead.created_at', read_only=True)
    salesperson_first_name = serializers.CharField(source='client.salesperson.first_name', read_only=True, default=None)
    salesperson_last_name = serializers.CharField(source='client.salesperson.last_name', read_only=True, default=None)
    

    class Meta:
        model = QuotationOrderModel
        exclude = ['contract']

    def get_quotation_date_display(self, obj):
        if obj.quotation_date:
            return obj.quotation_date.strftime('%d-%m-%Y')
        return None


class QuotationItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.product_description', read_only=True)
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = QuotationItem
        fields = "__all__"   

    def format_currency(self, value):
        # Format float or Decimal with commas and 2 decimal places
        return "{:,.2f}".format(value)

    def get_unit_price(self, obj):
        return self.format_currency(obj.unit_price)

    def get_total(self, obj):
        return self.format_currency(obj.total)

    def get_sgst(self, obj):
        return self.format_currency(obj.sgst)

    def get_cgst(self, obj):
        return self.format_currency(obj.cgst)

    def get_sub_total(self, obj):
        return self.format_currency(obj.sub_total)

    def get_quantity(self, obj):
        q = obj.quantity
        return int(q) if q == int(q) else float(q)
 
        
class NewQuotationOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationOrderModel
        fields = '__all__'


class NewQuotationItemSerializer(serializers.ModelSerializer):
    quotation = NewQuotationOrderSerializer()

    class Meta:
        model = QuotationItem
        fields = ['quotation', 'product', 'quantity'] 

 

class PrintQuotationOrderSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True)
    client = CustomerSerializer()
    salesperson = serializers.SerializerMethodField()
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    termsandconditions = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    contract_title = serializers.CharField(source='contract.title', read_only=True)
    contract = serializers.SerializerMethodField()
    lead_number = serializers.CharField(source='lead.lead_number', read_only=True)
    lead_date = serializers.DateTimeField(source='lead.created_at', read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = QuotationOrderModel
        fields = '__all__'
    
    def format_price(self, price):
        try:
            return "{:,.2f}".format(float(price))
        except (ValueError, TypeError):
            return price
    
    def get_salesperson(self, obj):
        if obj.client and obj.client.salesperson:
            return SalesPersonSerializer(obj.client.salesperson).data
        return None
    
    def get_grand_total(self, obj):
        return self.format_price(obj.grand_total)
    
    def get_termsandconditions(self, obj):
        terms = obj.termsandconditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data
    
    def get_subtotal(self, obj):
        subtotal = sum(item.sub_total for item in obj.items.all())
        return "{:,.2f}".format(subtotal)

    def get_total(self, obj):
        # If total includes taxes outside the sub_total, sum accordingly
        # But usually sub_total includes taxes, so sum sub_total is enough
        total = sum(item.total for item in obj.items.all())
        return "{:,.2f}".format(total)
    
    def get_contract(self, obj):
        contract = obj.contract
        if not contract:
            return None

        contract_data = {
            **contract.__dict__,
            'sections': []
        }
        contract_data.pop('_state', None)

        for section in contract.sections.all():
            section_data = {
                **section.__dict__,
                'points': list(section.points.values())
            }
            section_data.pop('_state', None)
            contract_data['sections'].append(section_data)

        return contract_data




        
class NewsalesOrderSerializer(serializers.ModelSerializer):
    client_firstname = serializers.CharField(source='customer.first_name', read_only=True)
    client_lastname = serializers.CharField(source='customer.last_name', read_only=True)
    mobile_number = serializers.CharField(source='customer.mobile', read_only=True)
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)
    bank_account_number = serializers.CharField(source='bank_account.account_number', read_only=True)
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    salesperson_name = serializers.CharField(source='customer.salesperson.first_name', read_only=True)
    class Meta:
        model = SalesOrderModel
        fields = '__all__'
        read_only_fields = (
            'sales_order_number', 
            'grand_total', 
            'client_name',
             'mobile_number', 
             'bank_name', 
             'bank_account_number', 
             'termsandconditions_title', 
             'is_delivered',
             'salesperson_name',
             )

# class SalesOrderItemSerializer(serializers.ModelSerializer):
#     product_name = serializers.CharField(source='product.name', read_only=True)
#     product_description = serializers.CharField(source='product.product_description', read_only=True)
#     quantity = serializers.SerializerMethodField()
#     pending_quantity = serializers.SerializerMethodField()
    
#     class Meta:
#         model = SalesOrderItem
#         fields = '__all__'
    
#     def get_quantity(self, obj):
#         q = obj.quantity
#         return int(q) if q == int(q) else float(q)
    
#     def get_pending_quantity(self, obj):
#         q = obj.pending_quantity
#         return int(q) if q == int(q) else float(q)
    

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.product_description', read_only=True)
    quantity = serializers.SerializerMethodField()
    pending_quantity = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    sgst = serializers.SerializerMethodField()
    cgst = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrderItem
        fields = '__all__'

    def get_quantity(self, obj):
        q = obj.quantity
        return int(q) if q == int(q) else float(q)

    def get_pending_quantity(self, obj):
        q = obj.pending_quantity
        return int(q) if q == int(q) else float(q)

    def format_currency(self, value):
        # Format float or Decimal with commas and 2 decimal places
        return "{:,.2f}".format(value)

    def get_unit_price(self, obj):
        return self.format_currency(obj.unit_price)

    def get_total(self, obj):
        return self.format_currency(obj.total)

    def get_sgst(self, obj):
        return self.format_currency(obj.sgst)

    def get_cgst(self, obj):
        return self.format_currency(obj.cgst)

    def get_sub_total(self, obj):
        return self.format_currency(obj.sub_total)


class SalesOrderItemOnlySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.product_description', read_only=True)
    
    class Meta:
        model = SalesOrderItem
        fields = '__all__'

class PrintSalesOrderSerializer(serializers.ModelSerializer):
    bank = serializers.SerializerMethodField()
    items = SalesOrderItemSerializer(many=True, read_only=True)
    customer = CustomerSerializer(read_only=True)
    salesperson = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    termsandconditions = serializers.SerializerMethodField()
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)

    class Meta:
        model = SalesOrderModel
        fields = '__all__'
        read_only_fields = (
            'sales_order_number', 
            'termsandconditions_title', 
            'grand_total',
            'customer', 
            'bank', 
            'items', 
            'salesperson', 
            'subtotal', 
            'total'
        )

    def get_bank(self, obj):
        bank = obj.bank_account
        return BankAccountSerializer(bank).data if bank else None

    def get_salesperson(self, obj):
        # Get salesperson via customer relation
        if obj.customer and obj.customer.salesperson:
            return SalesPersonSerializer(obj.customer.salesperson).data
        return None

    
    def get_subtotal(self, obj):
        subtotal = sum(item.sub_total for item in obj.items.all())
        return "{:,.2f}".format(subtotal)

    def get_total(self, obj):
        # If total includes taxes outside the sub_total, sum accordingly
        # But usually sub_total includes taxes, so sum sub_total is enough
        total = sum(item.total for item in obj.items.all())
        return "{:,.2f}".format(total)
    
    def get_termsandconditions(self, obj):
        terms = obj.termsandconditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data


class NewDeliverySerializer(serializers.ModelSerializer):
    client_firstname = serializers.CharField(source='customer.first_name', read_only=True)
    client_lastname = serializers.CharField(source='customer.last_name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    class Meta:
        model = DeliveryFormModel
        fields = '__all__'

class DeliveryItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.product_description', read_only=True)
    delivered_quantity = serializers.SerializerMethodField()
    class Meta:
        model = DeliveryItem
        fields = '__all__' 
    
    def get_delivered_quantity(self, obj):
        q = obj.delivered_quantity
        return int(q) if q == int(q) else float(q)


class PrintDeliveryItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.product_description', read_only=True)
    delivered_quantity = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    sgst = serializers.SerializerMethodField()
    cgst = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()
    class Meta:
        model = DeliveryItem
        fields = '__all__' 
    
    def get_delivered_quantity(self, obj):
        q = obj.delivered_quantity
        return int(q) if q == int(q) else float(q)

    def format_currency(self, value):
        # Format float or Decimal with commas and 2 decimal places
        return "{:,.2f}".format(value)

    def get_unit_price(self, obj):
        return self.format_currency(obj.unit_price)

    def get_total(self, obj):
        return self.format_currency(obj.total)

    def get_sgst(self, obj):
        return self.format_currency(obj.sgst)

    def get_cgst(self, obj):
        return self.format_currency(obj.cgst)

    def get_sub_total(self, obj):
        return self.format_currency(obj.sub_total)


class PrintDeliverySerializer(serializers.ModelSerializer):
    items = PrintDeliveryItemsSerializer(many=True, read_only=True)
    customer = CustomerSerializer(read_only=True)
    termsandconditions = serializers.SerializerMethodField()
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()
    salesperson = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryFormModel
        fields = '__all__'

    def get_subtotal(self, obj):
        subtotal = sum(item.sub_total for item in obj.items.all())
        return "{:,.2f}".format(subtotal)

    def get_total(self, obj):
        # If total includes taxes outside the sub_total, sum accordingly
        # But usually sub_total includes taxes, so sum sub_total is enough
        total = sum(item.total for item in obj.items.all())
        return "{:,.2f}".format(total)
    
    def get_salesperson(self, obj):
        # Get salesperson via customer relation
        if obj.customer and obj.customer.salesperson:
            return SalesPersonSerializer(obj.customer.salesperson).data
        return None
    
    def get_grand_total(self, obj):
        return "{:,.2f}".format(obj.grand_total)

    def get_termsandconditions(self, obj):
        # Get related TermsAndConditions
        terms = obj.termsandconditions
        # Get points related to this TermsAndConditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data

    


        

class InvoiceModelSerializer(serializers.ModelSerializer):
    client_firstname = serializers.CharField(source='client.first_name', read_only=True)
    client_lastname = serializers.CharField(source='client.last_name', read_only=True)
    # salesperson = serializers.CharField(source='salesperson.first_name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)

    class Meta:
        model = InvoiceModel
        fields = '__all__'  

class PrintInvoiceSerializer(serializers.ModelSerializer):
    client = CustomerSerializer(read_only=True)
    termsandconditions = serializers.SerializerMethodField()
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)
    salesperson = serializers.SerializerMethodField()
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    invoice_grand_total = serializers.SerializerMethodField()


    class Meta:
        model = InvoiceModel
        fields = '__all__'
    
    def get_invoice_grand_total(self, obj):
        return "{:,.2f}".format(obj.invoice_grand_total)
    
    def get_salesperson(self, obj):
        salesperson = obj.sales_order.customer.salesperson
        return SalesPersonSerializer(salesperson).data if salesperson else None

    def get_termsandconditions(self, obj):
        # Get related TermsAndConditions
        terms = obj.termsandconditions
        # Get points related to this TermsAndConditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data


class ReceiptSerializer(serializers.ModelSerializer):
    # termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    client_firstname = serializers.CharField(source='client.first_name', read_only=True)
    client_lastname = serializers.CharField(source='client.last_name', read_only=True)
    invoice_number = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptModel
        fields = '__all__'

    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number if obj.invoice else None

class PrintReceiptSerializer(serializers.ModelSerializer):
    # termsandconditions = serializers.SerializerMethodField()
    # termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    salesperson = serializers.SerializerMethodField()
    client = CustomerSerializer(read_only=True)
    invoice_number = serializers.SerializerMethodField()
    invoice_grand_total = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptModel
        fields = '__all__'

    def get_invoice_grand_total(self, obj):
        if obj.invoice and obj.invoice.invoice_grand_total is not None:
            return "{:,.2f}".format(obj.invoice.invoice_grand_total)
        return None  # or return None, depending on your use case
    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number if obj.invoice else None
        
    # def get_termsandconditions(self, obj):
    #     # Get related TermsAndConditions
    #     terms = obj.termsandconditions
    #     # Get points related to this TermsAndConditions
    #     points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
    #     return PrintTermsAndConditionsSerializer(points, many=True).data
    
    def get_salesperson(self, obj):
        salesperson = obj.client.salesperson
        return SalesPersonSerializer(salesperson).data if salesperson else None




class SalesReturnItemSerializer(serializers.ModelSerializer):
    delivery_item_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryItem.objects.all(),
        source='delivery_item',
        write_only=True
    )
    product_name = serializers.CharField(source='delivery_item.product.name', read_only=True)
    delivery_number = serializers.CharField(source='delivery_item.delivery_form.delivery_number', read_only=True)

    class Meta:
        model = SalesReturnItem
        fields = [
            'id', 'delivery_item_id', 'quantity',
            'unit_price', 'sgst_percentage', 'cgst_percentage',
            'total', 'sgst', 'cgst', 'sub_total',
            'product_name', 'delivery_number'
        ]
        read_only_fields = [
            'unit_price', 'sgst_percentage', 'cgst_percentage',
            'total', 'sgst', 'cgst', 'sub_total'
        ]

    def validate(self, data):
        delivery_item = data.get('delivery_item')
        quantity = data.get('quantity')

        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero")

        if quantity > delivery_item.net_quantity:
            raise serializers.ValidationError(
                f"Only {delivery_item.net_quantity} units available for return from this delivery item {delivery_item.id}"
            )

        if not delivery_item.delivery_form.is_invoiced:
            raise serializers.ValidationError("Cannot return from non-invoiced delivery")

        return data


class SalesReturnSerializer(serializers.ModelSerializer):
    items = SalesReturnItemSerializer(many=True)
    client_name = serializers.CharField(source='client.first_name', read_only=True)

    class Meta:
        model = SalesReturnModel
        fields = [
            'id', 'sales_return_number', 'return_date', 'client', 'client_name',
            'reason', 'grand_total', 'created_at', 'items', 'sales_order','termsandconditions'
        ]
        read_only_fields = ['grand_total', 'created_at']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one return item is required")
        return value

    def validate(self, data):
        """
        Ensure all delivery_items belong to the same sales_order selected in the parent.
        """
        sales_order = data.get('sales_order')
        items_data = self.initial_data.get('items', [])

        for item in items_data:
            delivery_item_id = item.get('delivery_item_id')
            try:
                delivery_item = DeliveryItem.objects.get(id=delivery_item_id)
            except DeliveryItem.DoesNotExist:
                raise serializers.ValidationError(f"Delivery item {delivery_item_id} does not exist.")

            delivery_sales_order = delivery_item.delivery_form.sales_order
            if delivery_sales_order.id != sales_order.id:
                raise serializers.ValidationError(
                    f"Delivery item {delivery_item_id} belongs to a different sales order "
                    f"({delivery_sales_order.sales_order_number}) than the one selected "
                    f"({sales_order.sales_order_number})."
                )

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            sales_return = SalesReturnModel.objects.create(**validated_data)
            for item_data in items_data:
                SalesReturnItem.objects.create(
                    sales_return=sales_return,
                    **item_data
                )
            return sales_return

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        with transaction.atomic():
            # Update top-level fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if items_data is not None:
                existing_items = {item.id: item for item in instance.items.all()}

                for item_data in items_data:
                    item_id = item_data.get('id', None)
                    if item_id and item_id in existing_items:
                        item = existing_items.pop(item_id)
                        for field, value in item_data.items():
                            setattr(item, field, value)
                        item.save()
                    else:
                        SalesReturnItem.objects.create(
                            sales_return=instance,
                            **item_data
                        )

                # Delete removed items
                for remaining_item in existing_items.values():
                    remaining_item.delete()

        return instance


    

class SalesReturnListSerializer(serializers.ModelSerializer):
    client_firstname = serializers.CharField(source='client.first_name', read_only=True)
    client_lastname = serializers.CharField(source='client.last_name', read_only=True)
    total_items = serializers.SerializerMethodField()
    saleperson = serializers.CharField(source='client.salesperson.first_name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)

    class Meta:
        model = SalesReturnModel
        fields = [
            'id', 'sales_return_number', 'return_date', 'client_firstname', 'client_lastname',
            'reason', 'grand_total', 'created_at', 'total_items', 'saleperson', 'sales_order_number'
        ]
    
    def get_total_items(self, obj):
        return obj.items.count() if obj.items else 0
    
class SalesReturnItemDisplaySerializer(serializers.ModelSerializer):
    delivery_item_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryItem.objects.all(),
        source='delivery_item',
        write_only=True
    )
    product_name = serializers.CharField(source='delivery_item.product.name', read_only=True)
    delivery_number = serializers.CharField(source='delivery_item.delivery_form.delivery_number', read_only=True)
    invoice_number = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SalesReturnItem
        fields = '__all__'
    
    def get_invoice_number(self, obj):
        # Find the invoice linked to the delivery_form of this delivery_item
        delivery_form = obj.delivery_item.delivery_form
        invoice_item = InvoiceItem.objects.filter(delivary=delivery_form).first()
        if invoice_item:
            return invoice_item.invoice.invoice_number
        return None

class SalesReturnDetailDisplaySerializer(serializers.ModelSerializer):
    items = SalesReturnItemDisplaySerializer(many=True, read_only=True)
    client_firstname = serializers.CharField(source='client.first_name', read_only=True)
    client_lastname = serializers.CharField(source='client.last_name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    termsandconditions_points = serializers.SerializerMethodField()
    class Meta:
        model = SalesReturnModel
        fields = '__all__'
    
    def get_termsandconditions_points(self, obj):
        terms = getattr(obj, 'termsandconditions', None)
        if terms:
            points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
            return PrintTermsAndConditionsSerializer(points, many=True).data
        return []
        

class SalesReturnPrintSerializer(serializers.ModelSerializer):
    items = SalesReturnItemDisplaySerializer(many=True, read_only=True)
    client = CustomerSerializer(read_only=True)
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    termsandconditions_points = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    grand_total_display = serializers.SerializerMethodField()
    salesperson = serializers.SerializerMethodField()
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)

    class Meta:
        model = SalesReturnModel
        fields = '__all__'

    def get_subtotal(self, obj):
        subtotal = sum(item.sub_total for item in obj.items.all())
        return "{:,.2f}".format(subtotal)

    def get_total(self, obj):
        total = sum(item.total for item in obj.items.all())
        return "{:,.2f}".format(total)

    def get_grand_total_display(self, obj):
        return "{:,.2f}".format(obj.grand_total)

    def get_salesperson(self, obj):
        if obj.client and obj.client.salesperson:
            return SalesPersonSerializer(obj.client.salesperson).data
        return None

    def get_termsandconditions_points(self, obj):
        terms = getattr(obj, 'termsandconditions', None)
        if terms:
            points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
            return PrintTermsAndConditionsSerializer(points, many=True).data
        return []

    
        
class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['name', 'flag']
        
class StateSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='country.name')
    class Meta:
        model = Country
        fields = ['name', 'country']
        
                
class CustomerSerializer(serializers.ModelSerializer):
    salesperson_id = serializers.PrimaryKeyRelatedField(
        queryset=SalesPerson.objects.all(),
        source='salesperson'
    )
    salesperson_name = serializers.SerializerMethodField()
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_type', 'first_name', 'last_name',
            'salesperson_id', 'salesperson_name',
            'country', 'state', 'company_name', 'address',
            'email', 'phone', 'mobile'
        ]
    def get_salesperson_name(self, obj):
        if obj.salesperson:
            return f"{obj.salesperson.first_name} {obj.salesperson.last_name}".strip()
        return None    

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'  # Include all fields in the serializer  


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'                      
        
class QuotationItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating only quantity and unit_price of a QuotationItem
    """
    class Meta:
        model = QuotationItem
        fields = ['quantity', 'unit_price', 'sgst_percentage', 'cgst_percentage']
        
    def validate(self, data):
        """
        Validate that quantity is greater than zero if provided
        """
        if 'quantity' in data and data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero")
        
        if 'unit_price' in data and data['unit_price'] < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
            
        return data        
    
class ProductSerializer(serializers.ModelSerializer):
    # Input fields
    unit = serializers.CharField(write_only=True)
    category = serializers.CharField(write_only=True)
    
    # Output fields
    unit_id = serializers.IntegerField(source='unit.id', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)

    category_id = serializers.IntegerField(source='category.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    def validate_unit(self, value):
        try:
            if str(value).isdigit():
                return Unit.objects.get(id=value)
            return Unit.objects.get(name=value)
        except Unit.DoesNotExist:
            raise serializers.ValidationError(f"Unit '{value}' does not exist.")



    def validate_category(self, value):
        try:
            if value.isdigit():
                return Category.objects.get(id=value)
            else:
                return Category.objects.get(name=value)
        except Category.DoesNotExist:
            raise serializers.ValidationError(f"Category '{value}' does not exist.")

    def create(self, validated_data):
        unit_instance = validated_data.pop('unit')
        category_instance = validated_data.pop('category')

        validated_data['unit'] = unit_instance
        validated_data['category'] = category_instance

        return Product.objects.create(**validated_data)

class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = ['id', 'title', 'created_at']

class TermsAndConditionsPointSerializer(serializers.ModelSerializer):
    terms_and_conditions_title = serializers.CharField(source='terms_and_conditions.title', read_only=True)
    class Meta:
        model = TermsAndConditionsPoint
        fields = ['id', 'terms_and_conditions', 'terms_and_conditions_title', 'point', 'created_at']




# class PurchaseOrderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PurchaseOrder
#         fields = ['id', 'supplier', 'purchase_order_number', 'purchase_order_date', 'contact_person_name', 'contact_person_number', 'quotation_number', 'remark', 'terms_and_conditions']



# class PurchaseOrderItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PurchaseOrderItem
#         fields = ['id', 'purchase_order', 'product', 'quantity', 'unit_price', 'total', 'sgst_percentage', 'cgst_percentage', 'sub_total']




class PurchaseOrderListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.first_name', read_only=True)
    total_items = serializers.SerializerMethodField()
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'purchase_order_date', 'purchase_order_number', 'supplier_name',
            'total_items', 'contact_person_number', 'grand_total',
        ]
    
    def get_total_items(self, obj):
        total_items = obj.items.count()
        return total_items if total_items else 0

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.product_description', read_only=True)
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'product_name', 'product_description', 'quantity', 'unit_price', 'total',
            'sgst_percentage', 'cgst_percentage', 'sub_total'
        ]

    def validate(self, data):
        """
        Validate that unit_price and quantities are positive numbers
        """
        if 'unit_price' in data and data['unit_price'] < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        if 'quantity' in data and data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        return data

class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_id = serializers.IntegerField(source='supplier.id', read_only=True)
    supplier_name = serializers.CharField(source='supplier.first_name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, required=False)
    supplier_details = SupplierSerializer(source='supplier', read_only=True)
    terms_and_conditions_id = serializers.IntegerField(source='terms_and_conditions.id', read_only=True)
    terms_and_conditions_title = serializers.CharField(source='terms_and_conditions.title', read_only=True)
    termsandconditions = serializers.SerializerMethodField()
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'supplier', 'supplier_id', 'supplier_name', 'purchase_order_number', 'purchase_order_date',
            'contact_person_name', 'contact_person_number', 'quotation_number',
            'grand_total', 'remark', 'terms_and_conditions', 'terms_and_conditions_id', 'terms_and_conditions_title', 'termsandconditions', 'items', 'supplier_details'
        ]
        read_only_fields = ['supplier_name', 'termsandconditions']
        extra_kwargs = {
            'supplier': {'write_only': True},
            'terms_and_conditions': {'write_only': True},
        }

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)
            
        return purchase_order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        # Update PurchaseOrder fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle items update if provided
        if items_data is not None:
            # Delete existing items not in the update
            existing_item_ids = [item.id for item in instance.items.all()]
            updated_item_ids = [item.get('id') for item in items_data if item.get('id')]
            
            items_to_delete = set(existing_item_ids) - set(updated_item_ids)
            if items_to_delete:
                PurchaseOrderItem.objects.filter(id__in=items_to_delete).delete()
            
            # Create or update items
            for item_data in items_data:
                item_id = item_data.get('id')
                if item_id:
                    # Update existing item
                    item = PurchaseOrderItem.objects.get(id=item_id, purchase_order=instance)
                    for attr, value in item_data.items():
                        setattr(item, attr, value)
                    item.save()
                else:
                    # Create new item
                    PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
        
        return instance
    
    def get_termsandconditions(self, obj):
        if obj.terms_and_conditions:
            points = obj.terms_and_conditions.termsandconditionspoint_set.all()  # Assuming the related_name is 'points'
            return TermsAndConditionsPointSerializer(points, many=True).data
        return []
    




class MaterialReceiveListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.first_name', read_only=True)
    class Meta:
        model = MaterialReceive
        fields = [
            'id', 'received_date', 'material_receive_number', 'supplier_name'
        ]


class MaterialReceiveItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_description = serializers.CharField(source='product.product_description', read_only=True)
    class Meta:
        model = MaterialReceiveItem
        fields = [
            'id', 'product', 'product_name', 'product_description', 'quantity', 'unit_price', 'total',
            'sgst_percentage', 'cgst_percentage', 'sub_total'
        ]

    def validate(self, data):
        if 'unit_price' in data and data['unit_price'] < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        if 'quantity' in data and data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        return data

class MaterialReceiveSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.first_name', read_only=True)
    purchase_order_number = serializers.CharField(source='purchase_order.purchase_order_number', read_only=True)
    items = MaterialReceiveItemSerializer(many=True, required=False)
    
    class Meta:
        model = MaterialReceive
        fields = [
            'id', 'supplier', 'supplier_name', 'purchase_order', 'purchase_order_number', 'material_receive_number', 'grand_total', 'received_date', 'remark', 'items'
        ]
        read_only_fields = ['supplier_name', 'purchase_order_number']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        material_receive = MaterialReceive.objects.create(**validated_data)
        
        for item_data in items_data:
            MaterialReceiveItem.objects.create(material_receive=material_receive, **item_data)
            product = item_data.get('product')
            product.stock += item_data.get('quantity', 0)
            product.save()
            print("item_data", item_data.get('product').stock)
            
        return material_receive

    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        # Update the MaterialReceive instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            processed_ids = []

            for item_data in items_data:
                item_id = item_data.get('id')
                product = item_data.get('product')
                quantity = item_data.get('quantity', 0)

                if item_id:
                    try:
                        item = MaterialReceiveItem.objects.get(id=item_id, material_receive=instance)

                        # Revert old quantity from stock
                        item.product.stock -= item.quantity

                        # Update the item fields
                        for attr, value in item_data.items():
                            setattr(item, attr, value)
                        item.save()

                        # Add new quantity to stock
                        item.product.stock += quantity
                        item.product.save()

                        processed_ids.append(item.id)

                    except MaterialReceiveItem.DoesNotExist:
                        continue
                else:
                    # Create new item
                    item = MaterialReceiveItem.objects.create(material_receive=instance, **item_data)

                    # Adjust stock
                    item.product.stock += quantity
                    item.product.save()

                    processed_ids.append(item.id)

            # Delete items not included in update
            items_to_delete = MaterialReceiveItem.objects.filter(material_receive=instance).exclude(id__in=processed_ids)
            for item in items_to_delete:
                # Revert stock before deletion
                item.product.stock -= item.quantity
                item.product.save()
                item.delete()

        return instance






class ContractPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractPoint
        fields = ['id', 'points', 'section']


class ContractSectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContractSection
        fields = ['id', 'title', 'contract']


class ContractSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contract
        fields = ['id', 'title', 'created_at']


class ContractSectionDetailSerializer(serializers.ModelSerializer):
    points = ContractPointSerializer(many=True, read_only=True)
    class Meta:
        model = ContractSection
        fields = ['id', 'title', 'contract', 'points']


class ContractDetailSerializer(serializers.ModelSerializer):
    sections = ContractSectionDetailSerializer(many=True, read_only=True)
    class Meta:
        model = Contract
        fields = ['id', 'title', 'created_at', 'sections']