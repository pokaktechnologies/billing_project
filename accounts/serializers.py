from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import *

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
        
# class SalesOrderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SalesOrder
#         fields = [
#             'id', 
#             'customer_name', 
#             'invoice_no', 
#             'invoice_date', 
#             'terms', 
#             'due_date', 
#             'salesperson', 
#             'subject', 
#             'attachments', 
#             'order_amount',
#             'quantity'
#         ]
#         readonly_fields = ['order_number', 'invoice_no']
        
# class QuotationOrderSerializer(serializers.ModelSerializer):
#     salesperson_name = serializers.CharField(source='salesperson.display_name', read_only=True)

#     class Meta:
#         model = QuotationOrderModel
#         fields = [
#             'id',
#             'customer_name',
#             'quotation_number',
#             'quotation_date',
#             'terms',
#             'due_date',
#             'salesperson',
#             'salesperson_name',  # Salesperson fetched dynamically
#             'email_id',
#             'subject',
#             'attachments',
#             'item_name',
#             'description',
#             'unit_price',
#             'discount',
#             'total_amount',
#             'quantity'
#         ]
#         read_only_fields = ['quotation_number', 'total_amount']

#     def validate_discount(self, value):
#         """ Ensure discount is not greater than unit price """
#         if value < 0:
#             raise serializers.ValidationError("Discount cannot be negative.")
#         return value
    



            
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
    unit = serializers.CharField()  #
    category=serializers.CharField()
    
    class Meta:
        model = Product
        fields = ['id','name', 'product_description', 'unit', 'unit_price', 'category']
        

    def validate_unit(self, value):
        """Fetch and return the Unit instance based on its name."""
        try:
            return Unit.objects.get(name=value)
        except Unit.DoesNotExist:
            raise serializers.ValidationError(f"Unit '{value}' does not exist.")

    def validate_category(self, value):
        """Fetch and return the Category instance based on its name or ID."""
        try:
            # You can modify this logic based on your input (name or ID)
            if value.isdigit():  # Check if it's an ID
                return Category.objects.get(id=value)
            else:  # Otherwise, assume it's a category name
                return Category.objects.get(name=value)
        except Category.DoesNotExist:
            raise serializers.ValidationError(f"Category '{value}' does not exist.")

    def create(self, validated_data):
        """Override create method to handle unit and category assignment."""
        unit_instance = validated_data.pop('unit')  # `unit` is already validated as a Unit instance
        category_instance = validated_data.pop('category')  # `category` is also validated as a Category instance

        validated_data['unit'] = unit_instance
        validated_data['category'] = category_instance

        return Product.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Override update method to handle unit and category assignment."""
        unit_instance = validated_data.pop('unit', None)
        category_instance = validated_data.pop('category', None)

        if unit_instance:
            instance.unit = unit_instance  # Assign Unit instance
        if category_instance:
            instance.category = category_instance  # Assign Category instance

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    

        
 

class SalesPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesPerson
        fields = '__all__'
        read_only_fields = []        
        
        
class QuotationOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationOrderModel
        fields = '__all__'


class QuotationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationItem
        fields = '__all__'               
        
class NewQuotationOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationOrderModel
        fields = '__all__'


class NewQuotationItemSerializer(serializers.ModelSerializer):
    quotation = NewQuotationOrderSerializer()
    class Meta:
        model = QuotationItem
        fields = ['quotation', 'product', 'quantity']           
        
class NewsalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderModel
        fields = '__all__'
        read_only_fields = ('sales_order_id', 'grand_total')  # Ensure correct spelling

class NewDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryFormModel
        fields = '__all__'        
        
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
    class Meta:
        model = Customer
        fields = '__all__'                

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