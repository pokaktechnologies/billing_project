from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, Quotation,Product, Feature, HelpLink, Notification, UserSetting, Feedback, SalesOrder,QuotationOrder, InvoiceOrder, DeliveryOrder, SupplierPurchase,Supplier,DeliveryChallan

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
        
class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = [
            'id', 
            'customer_name', 
            'invoice_no', 
            'invoice_date', 
            'terms', 
            'due_date', 
            'salesperson', 
            'subject', 
            'attachments', 
            'order_amount',
            'quantity'
        ]
        readonly_fields = ['order_number', 'invoice_no']
        
class QuotationOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationOrder
        fields = [
            'id',
            'customer_name',
            'quotation_number',
            'quotation_date',
            'terms',
            'due_date',
            'salesperson',
            'subject',
            'attachments',
            'customer_amount',
            'quantity'
        ]
        read_only_fields = ['quotation_number']

class InvoiceOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceOrder
        fields = [
            'id',
            'customer_name',
            'invoice_number',
            'invoice_date',
            'terms',
            'due_date',
            'salesperson',
            'subject',
            'attachments',
            'invoice_amount',
            'quantity'
        ]
        read_only_fields = ['invoice_number']

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
        
class SupplierPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPurchase
        fields = [
                'id', 'supplier_name', 'purchase_number', 'date', 'amount', 'terms', 
                'due_date', 'purchase_person', 'subject', 'add_stock', 'attachments','quantity'
            ]
        read_only_fields = ['supplier_number']        
        

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'supplier_type', 'first_name', 'last_name', 'company_name',
            'supplier_display_name', 'email', 'phone', 'mobile', 'currency', 'payment_terms'
        ]        
        
class DeliveryChallanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryChallan
        fields = '__all__'
        
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'stock']        
 
        