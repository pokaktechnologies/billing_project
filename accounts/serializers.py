from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import *
import random

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
    class Meta:
        model = SalesPerson
        fields = '__all__'
        read_only_fields = []        
        
        
class QuotationOrderSerializer(serializers.ModelSerializer):
    quotation_date = serializers.SerializerMethodField()
    class Meta:
        model = QuotationOrderModel
        fields = '__all__'
    
    def get_quotation_date(self, obj):
        # Format: DD-MM-YYYY
        if obj.quotation_date:
            return obj.quotation_date.strftime('%d-%m-%Y')
        return None

class QuotationItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.SerializerMethodField()
    class Meta:
        model = QuotationItem
        fields = ['quotation', 'product','quantity','unit_price','sgst_percentage','cgst_percentage','total','sgst','cgst','sub_total']   
    def get_unit_price(self, obj):
        if obj.unit_price == 0:
            return obj.product.unit_price
        return obj.unit_price            
        
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
    client_name = serializers.CharField(source='customer.first_name', read_only=True)
    mobile_number = serializers.CharField(source='customer.mobile', read_only=True)
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)
    bank_account_number = serializers.CharField(source='bank_account.account_number', read_only=True)
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)

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
             'is_delivered'
             )

class SalesOrderItemSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = SalesOrderModel
        fields = '__all__'
        read_only_fields = ('sales_order_number', 'grand_total','customer', 'bank', 'items', 'salesperson', 'subtotal', 'total')

    def get_bank(self, obj):
        bank = obj.bank_account
        return BankAccountSerializer(bank).data if bank else None

    def get_salesperson(self, obj):
        salesperson = obj.customer.salesperson
        return SalesPersonSerializer(salesperson).data if salesperson else None
    
    def get_subtotal(self, obj):
        #calculate subtotal from items
        subtotal = 0
        for item in obj.items.all():
            subtotal += item.sub_total
        return subtotal

    def get_total(self, obj):
        total = 0
        for item in obj.items.all():
            total += item.sub_total + item.sgst + item.cgst  # Add SGST and CGST to subtotal
        return total
    
    def get_termsandconditions(self, obj):
        # Get related TermsAndConditions
        terms = obj.termsandconditions
        # Get points related to this TermsAndConditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data

class NewDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryFormModel
        fields = '__all__'    

class DeliveryItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryItem
        fields = '__all__' 





class PrintDeliverySerializer(serializers.ModelSerializer):
    items = DeliveryItemsSerializer(many=True, read_only=True)
    customer = CustomerSerializer(read_only=True)
    termsandconditions = serializers.SerializerMethodField()
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)

    class Meta:
        model = DeliveryFormModel
        fields = '__all__'

    def get_termsandconditions(self, obj):
        # Get related TermsAndConditions
        terms = obj.termsandconditions
        # Get points related to this TermsAndConditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data

    


        

class InvoiceModelSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.first_name', read_only=True)
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

    class Meta:
        model = InvoiceModel
        fields = '__all__'
    
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
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    client_name = serializers.CharField(source='client.first_name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = ReceiptModel
        fields = '__all__'
        # extra_kwargs = {
        #     'receipt_number': {'read_only': True}
        # }
    
    # def create(self, validated_data):
    #     # Generate a receipt number like "RP1234"
    #     receipt_number = f"REC-{random.randint(10000, 99999)}"

    #     # Ensure uniqueness (since receipt_number is unique=True)
    #     while ReceiptModel.objects.filter(receipt_number=receipt_number).exists():
    #         receipt_number = f"REC-{random.randint(10000, 99999)}"

    #     validated_data['receipt_number'] = receipt_number
    #     return super().create(validated_data)

class PrintReceiptSerializer(serializers.ModelSerializer):
    termsandconditions = serializers.SerializerMethodField()
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    salesperson = serializers.SerializerMethodField()
    client = CustomerSerializer(read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    invoice_grand_total = serializers.CharField(source='invoice.invoice_grand_total', read_only=True)

    class Meta:
        model = ReceiptModel
        fields = '__all__'
    
    def get_termsandconditions(self, obj):
        # Get related TermsAndConditions
        terms = obj.termsandconditions
        # Get points related to this TermsAndConditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data
    
    def get_salesperson(self, obj):
        salesperson = obj.client.salesperson
        return SalesPersonSerializer(salesperson).data if salesperson else None



    

        
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
    unit = serializers.CharField()  #
    category=serializers.CharField()
        # Output fields
    category_id = serializers.IntegerField(source='category.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    salesperson_id=serializers.PrimaryKeyRelatedField(
        queryset=SalesPerson.objects.all(), source='salesperson'
    )
    # Display salesperson name in response
    salesperson_name=serializers.SerializerMethodField()

    
    
    class Meta:
        model = Product
        fields = ['id','name', 'product_description', 'unit', 'unit_price', 'category','category_id','category_name','sgst','cgst','salesperson_id','salesperson_name']
        
    def get_salesperson_name(self, obj):
        if obj.salesperson:
            return f"{obj.salesperson.first_name} {obj.salesperson.last_name}".strip()
        return None
    
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
        category_instance = validated_data.pop('category')
        # salesperson_instance = validated_data.pop('salesperson')
        # `category` is also validated as a Category instance

        validated_data['unit'] = unit_instance
        validated_data['category'] = category_instance
        # validated_data['salesperson'] = salesperson_instance

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