from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import *
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
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = QuotationItem
        fields = "__all__"   

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
    class Meta:
        model = QuotationOrderModel
        fields = '__all__'
    
    def get_salesperson(self, obj):
        salesperson = obj.client.salesperson
        return SalesPersonSerializer(salesperson).data if salesperson else None

    def get_termsandconditions(self, obj):
        # Get related TermsAndConditions
        terms = obj.termsandconditions
        # Get points related to this TermsAndConditions
        points = TermsAndConditionsPoint.objects.filter(terms_and_conditions=terms)
        return PrintTermsAndConditionsSerializer(points, many=True).data
    
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
    
    def get_contract(self, obj):
        contract = obj.contract
        if not contract:
            return None

        # Convert contract to dict
        contract_data = {
            **contract.__dict__,
            'sections': []
        }
        contract_data.pop('_state', None)  # Remove internal Django field

        for section in contract.sections.all():
            section_data = {
                **section.__dict__,
                'points': list(section.points.values())
            }
            section_data.pop('_state', None)
            contract_data['sections'].append(section_data)

        return contract_data



        
class NewsalesOrderSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='customer.first_name', read_only=True)
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
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)


    class Meta:
        model = SalesOrderModel
        fields = '__all__'
        read_only_fields = ('sales_order_number', "termsandconditions_title" 'grand_total','customer', 'bank', 'items', 'salesperson', 'subtotal', 'total')

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
    client_firstname = serializers.CharField(source='customer.first_name', read_only=True)
    client_lastname = serializers.CharField(source='customer.last_name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.sales_order_number', read_only=True)
    termsandconditions_title = serializers.CharField(source='termsandconditions.title', read_only=True)
    class Meta:
        model = DeliveryFormModel
        fields = '__all__'    

class DeliveryItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
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




# class PurchaseOrderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PurchaseOrder
#         fields = ['id', 'supplier', 'purchase_order_number', 'purchase_order_date', 'contact_person_name', 'contact_person_number', 'quotation_number', 'remark', 'terms_and_conditions']



# class PurchaseOrderItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PurchaseOrderItem
#         fields = ['id', 'purchase_order', 'product', 'quantity', 'unit_price', 'total', 'sgst_percentage', 'cgst_percentage', 'sub_total']




class PurchaseOrderListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.supplier_display_name', read_only=True)
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
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'quantity', 'unit_price', 'total',
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
    supplier_name = serializers.CharField(source='supplier.supplier_display_name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, required=False)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'supplier', 'supplier_name', 'purchase_order_number', 'purchase_order_date',
            'contact_person_name', 'contact_person_number', 'quotation_number',
            'grand_total', 'remark', 'terms_and_conditions', 'items'
        ]
        read_only_fields = ['supplier_name']

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
    




class MaterialReceiveListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.supplier_display_name', read_only=True)
    class Meta:
        model = MaterialReceive
        fields = [
            'id', 'received_date', 'material_receive_number', 'supplier_name'
        ]


class MaterialReceiveItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialReceiveItem
        fields = [
            'id', 'product', 'quantity', 'unit_price', 'total',
            'sgst_percentage', 'cgst_percentage', 'sub_total'
        ]

    def validate(self, data):
        if 'unit_price' in data and data['unit_price'] < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        if 'quantity' in data and data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        return data

class MaterialReceiveSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.supplier_display_name', read_only=True)
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