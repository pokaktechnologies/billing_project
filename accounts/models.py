from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now
from decimal import Decimal
from django_countries.fields import CountryField


class CustomUserManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, password=None):
        if not email:
            raise ValueError("The Email field is required")
        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, password):
        user = self.create_user(first_name, last_name, email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
    

    
class CustomUser(AbstractBaseUser, PermissionsMixin):     
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    is_otp_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # New fields for organization details
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    business_location = models.CharField(max_length=255, blank=True, null=True)
    state_province = models.CharField(max_length=255, blank=True, null=True)

    country = CountryField(blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    pin_code = models.CharField(max_length=10, blank=True, null=True)
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

class Quotation(models.Model):
    customer_name = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=50, unique=True)
    order_number = models.CharField(max_length=50, blank=True, null=True)
    invoice_date = models.DateField(default=now)
    terms = models.CharField(max_length=255, default="Due on Receipt")
    due_date = models.DateField(blank=True, null=True)
    salesperson = models.CharField(max_length=255, blank=True, null=True)
    subject = models.TextField(blank=True, null=True)
    delivery_location = models.CharField(max_length=255, blank=True, null=True)
    received_location = models.CharField(max_length=255, blank=True, null=True)
    attachments = models.FileField(upload_to="quotations/", blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False, default=1)


    def __str__(self):
        return self.invoice_number


    
class BankAccount(models.Model):
    customer = models.ForeignKey(
        "Customer", on_delete=models.CASCADE, related_name="bank_accounts"
    )  
    bank_name = models.CharField(max_length=255)
    account_holder_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50, unique=True)
    ifsc_code = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"    
        
class Feature(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100)  # Icon name or URL
    link = models.URLField()  # Link for the feature

    def __str__(self):
        return self.name
    
 
class HelpLink(models.Model):
    title = models.CharField(max_length=100)
    icon = models.CharField(max_length=200)  # Path to the icon
    link = models.URLField()  # External or internal URL

    def __str__(self):
        return self.title

# Notifications
class Notification(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# Settings
class UserSetting(models.Model):
    RATE_US_CHOICES = [
        ('great', '😊 Great'),
        ('okay', '😐 Okay'),
        ('bad', '😞 Bad')
    ]
     
    company_name = models.CharField(max_length=200)
    user_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)  # Upload folder for logos
    business_type = models.CharField(max_length=50, choices=[
        ('Individual', 'Individual'),
        ('Corporate', 'Corporate')
    ])
    contact_us = models.TextField(default=1)  # Contact details of the organization
    rate_us = models.CharField(max_length=5, choices=RATE_US_CHOICES, blank=True,default=1)  # Optional rating

    def __str__(self):
        return self.company_name
# Rate Us
class Feedback(models.Model):
    user = models.CharField(max_length=100)  # Or a ForeignKey to User model
    rating = models.IntegerField(choices=[
        (1, 'Bad'),
        (2, 'Okay'),
        (3, 'Great'),
    ])
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} - {self.rating}"   
    
class Product(models.Model):

    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('liter', 'Liter'),
        ('meter', 'Meter'),
        ('box', 'Box'),
        ('dozen', 'Dozen'),
    ]
      
    name = models.CharField(max_length=255)
    product_description = models.TextField(blank=True)
    unit = models.ForeignKey('Unit', on_delete=models.CASCADE, related_name='products')  # Connected as ForeignKey
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="SGST percentage (e.g. 9.00)")  
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="CGST percentage (e.g. 9.00)")  

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Unit name (e.g., kg, piece)
    description = models.TextField(blank=True)  # Optional description

    def __str__(self):
        return self.name
    
class SalesOrder(models.Model):
    customer_name = models.CharField(max_length=255)
    invoice_no = models.CharField(max_length=50, unique=True)
 
    order_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    terms = models.CharField(max_length=255, blank=True)
    due_date = models.DateField()
    salesperson = models.CharField(max_length=255)
    subject = models.TextField(blank=True)
    remark = models.CharField(max_length=255, blank=True)
    attachments = models.URLField(blank=True)
    order_amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False, default=1)


    def __str__(self):
        return f"Sales Order {self.order_number} - {self.customer_name}"  


# class QuotationOrder(models.Model):
#     customer_name = models.CharField(max_length=255)
#     quotation_number = models.CharField(max_length=50, unique=True)
#     quotation_date = models.DateField()
#     terms = models.CharField(max_length=255, blank=True)
#     due_date = models.DateField()
#     salesperson = models.CharField(max_length=255)
#     subject = models.TextField(blank=True)
#     attachments = models.URLField(blank=True)
#     customer_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     quantity = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False, default=1)

#     def __str__(self):
#         return f"Quotation {self.quotation_number} - {self.customer_name}"    

    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer_name}"    
    
class DeliveryOrder(models.Model):
    customer_name = models.CharField(max_length=255)
    delivery_number = models.CharField(max_length=50, unique=True)
    delivery_date = models.DateField()
    delivery_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_location = models.CharField(max_length=255)
    received_location = models.CharField(max_length=255)
    salesperson = models.CharField(max_length=255)
    terms = models.CharField(max_length=255, blank=True)
    due_date = models.DateField()
    subject = models.TextField(blank=True)
    attachments = models.URLField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False, default=1)

    
    def __str__(self):
        return f"Delivery {self.delivery_number} - {self.customer_name}"
    
# class SupplierPurchase(models.Model):
#     supplier_name = models.CharField(max_length=255)
#     purchase_number = models.CharField(max_length=50, unique=True, default='Unknown')
#     date = models.DateField()
#     product_name = models.CharField(max_length=255, default=1)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     terms = models.CharField(max_length=255, blank=True)
#     due_date = models.DateField()
#     purchase_person = models.CharField(max_length=255, default='Unknown')
#     subject = models.TextField(blank=True)
#     add_stock = models.BooleanField(default=False)
#     attachments = models.URLField(blank=True)
#     quantity = models.DecimalField(max_digits=10, decimal_places=2,null=False, blank=False , default=1)

#     def __str__(self):
#         return f"Purchase {self.supplier_number} - {self.supplier_name}"        
    
class Supplier(models.Model):
    SUPPLIER_TYPE_CHOICES = [
        ('Business', 'Business'),
        ('Individual', 'Individual'),
    ]
    
    supplier_number = models.CharField(max_length=50, unique=True)
    supplier_type = models.CharField(max_length=20, choices=SUPPLIER_TYPE_CHOICES)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField()
    date = models.DateField()
    contact_person_name = models.CharField(max_length=255, blank=True, null=True)
    contact_person_number = models.CharField(max_length=20, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    mobile = models.CharField(max_length=20)
    currency = models.CharField(max_length=10)
    payment_terms = models.ForeignKey('TermsAndConditions', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    def __str__(self):
        return self.company_name + " - " + self.contact_person_name


class DeliveryChallan(models.Model):
    customer_name = models.CharField(max_length=255)
    delivery_challan_number = models.CharField(max_length=50, unique=True)
    customer_note = models.TextField(blank=True)

    def __str__(self):
        return f"Delivery Challan {self.delivery_challan_number} - {self.customer_name}"  
    
class SalesPerson(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    mobile = models.CharField(max_length=15, unique=True)
    incentive = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField(blank=True, null=True)  # Full address field
    country = models.CharField(max_length=15,blank=True, null=True)  # Country field using django-countries
    state = models.CharField(max_length=100, blank=True, null=True)  # State/Region


    def __str__(self):
        return self.first_name    
    


    
class QuotationOrderModel(models.Model):
# Add ForeignKey
    # customer_name = models.CharField(max_length=255)
    client = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    quotation_number = models.CharField(max_length=50, unique=True)
    quotation_date = models.DateField()
    delivery_address = models.TextField(max_length=100, blank=True )  
    delivery_location = models.TextField(max_length=100, blank=True)
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.CASCADE, null=True, blank=True)
    contract = models.ForeignKey('Contract', on_delete=models.SET_NULL, null=True, blank=True)  
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def update_grand_total(self):
        """Recalculate grand total based on related QuotationItems."""
        total_amount = sum(item.sub_total for item in self.items.all())  # Sum of all items' sub_total
        self.grand_total = total_amount
        self.save(update_fields=["grand_total"])  # Save only the g

    def __str__(self):
        return f"Quotation {self.quotation_number} - {self.client}"    
    

class QuotationItem(models.Model):
    quotation = models.ForeignKey(QuotationOrderModel, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # product_description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    # discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Store SGST percentage
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Store CGST percentage
    # Auto-calculated field
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # quantity * unit_price
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% SGST
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% CGST
    
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # Total + SGST + CGST
    
    
    def save(self, *args, **kwargs):
        """Calculate and update total, SGST, CGST, and sub_total before saving."""
        # if self.unit_price == 0:  
        #     self.unit_price = self.product.unit_price  # Default if not
        # Use unit_price from the payload if provided; otherwise, fallback to product's unit_price
        # self.unit_price = self.unit_price
    
        if self.unit_price == 0:
            unit_price_decimal = self.product.unit_price
        else:
            unit_price_decimal = self.unit_price                
        unit_price_decimal = Decimal(unit_price_decimal)
        quantity_decimal = Decimal(self.quantity)
        sgst_percentage_decimal = Decimal(str(self.sgst_percentage))
        cgst_percentage_decimal = Decimal(str(self.cgst_percentage))
        
        self.total = unit_price_decimal * quantity_decimal
        self.sgst = ((sgst_percentage_decimal * unit_price_decimal) / Decimal(100)) * quantity_decimal
        self.cgst = ((cgst_percentage_decimal * unit_price_decimal) / Decimal(100)) * quantity_decimal
        self.sub_total = self.total + self.sgst + self.cgst
        super().save(*args, **kwargs)
        
        self.quotation.update_grand_total()

    def delete(self, *args, **kwargs):
        """Ensure grand total updates when an item is deleted."""
        super().delete(*args, **kwargs)
        self.quotation.update_grand_total()    

    def __str__(self):
        return self.product.name
    
    from django.db import models


class SalesOrderModel(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    sales_order_number = models.CharField(max_length=50, unique=True)
    sales_date = models.DateField()
    purchase_order_number = models.CharField(max_length=50, blank=True, null=True)
    remark = models.CharField(max_length=255, blank=True)
    delivery_location = models.CharField(max_length=255, blank=True)
    delivery_address = models.TextField(blank=True)
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.CASCADE,  null=True, blank=True)
    bank_account = models.ForeignKey(
        'BankAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name="sales_orders"
    )
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    is_delivered = models.BooleanField(default=False)

    def update_grand_total(self):
        total = sum(item.sub_total for item in self.items.all())
        self.grand_total = total
        self.save(update_fields=["grand_total"])

    def __str__(self):
        return f"Sales Order {self.sales_order_number} - {self.customer}"  # Use self.customer instead of customer_name


class SalesOrderItem(models.Model):
    sales_order = models.ForeignKey(SalesOrderModel, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    pending_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    is_item_delivered = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """Calculate and update total, SGST, CGST, and sub_total before saving."""
        # if self.unit_price == 0:  
        #     self.unit_price = self.product.unit_price  # Default if not
        # Use unit_price from the payload if provided; otherwise, fallback to product's unit_price
        # self.unit_price = self.unit_price
    
        if self.unit_price == 0:
            unit_price_decimal = self.product.unit_price
        else:
            unit_price_decimal = self.unit_price                
        unit_price_decimal = Decimal(unit_price_decimal)
        quantity_decimal = Decimal(self.quantity)
        sgst_percentage_decimal = Decimal(str(self.sgst_percentage))
        cgst_percentage_decimal = Decimal(str(self.cgst_percentage))
        
        self.total = unit_price_decimal * quantity_decimal

        self.sgst = ((sgst_percentage_decimal * unit_price_decimal) / Decimal(100)) * quantity_decimal
        self.cgst = ((cgst_percentage_decimal * unit_price_decimal) / Decimal(100)) * quantity_decimal
        self.sub_total = self.total + self.sgst + self.cgst
        super().save(*args, **kwargs)
        
        self.sales_order.update_grand_total()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.sales_order:
            self.sales_order.update_grand_total()

    def __str__(self):
        return f"{self.product.name} - {self.sales_order.sales_order_number}"  # Use sales_order_id for clarity


    
    
class DeliveryFormModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE,null=True, blank=True)
    delivery_number = models.CharField(max_length=50, unique=True)
    delivery_date = models.DateField()
    sales_order = models.ForeignKey(SalesOrderModel, on_delete=models.CASCADE, related_name="deliveries")
    delivery_location = models.CharField(max_length=255, blank=True)
    delivery_address = models.TextField(blank=True)
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.CASCADE,  null=True, blank=True)
    time = models.TimeField()
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    is_invoiced = models.BooleanField(default=False)

    def update_grand_total(self):
        total_amount = sum(item.sub_total for item in self.items.all())
        self.grand_total = total_amount
        self.save(update_fields=["grand_total"])

    def __str__(self):
        return f"Delivery {self.delivery_number} - {self.customer}"


class DeliveryItem(models.Model):
    delivery_form = models.ForeignKey(DeliveryFormModel, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # sales_order_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    delivered_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def save(self, *args, **kwargs):
        # Price calculations
        if self.unit_price == 0:
            unit_price_decimal = self.product.unit_price
        else:
            unit_price_decimal = self.unit_price                
        unit_price_decimal = Decimal(unit_price_decimal)
        quantity_decimal = Decimal(self.delivered_quantity)
        sgst_percentage_decimal = Decimal(str(self.sgst_percentage))
        cgst_percentage_decimal = Decimal(str(self.cgst_percentage))

        self.total = unit_price_decimal * quantity_decimal
        self.sgst = ((sgst_percentage_decimal * unit_price_decimal) / Decimal(100)) * quantity_decimal
        self.cgst = ((cgst_percentage_decimal * unit_price_decimal) / Decimal(100)) * quantity_decimal
        self.sub_total = self.total + self.sgst + self.cgst

        super().save(*args, **kwargs)


        # Update the DeliveryForm grand total
        self.delivery_form.update_grand_total()


    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.delivery_form.update_grand_total()

    def __str__(self):
        return self.product.name 


class InvoiceModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    client = models.ForeignKey('Customer', on_delete=models.CASCADE,null=True, blank=True)
    sales_order = models.ForeignKey(SalesOrderModel, on_delete=models.CASCADE)
    # delivery = models.ForeignKey(DeliveryFormModel, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.CASCADE, null=True, blank=True)
    remark = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    is_receipted = models.BooleanField(default=False)

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(InvoiceModel, related_name='items', on_delete=models.CASCADE)
    delivary = models.ManyToManyField(DeliveryFormModel)


class ReceiptModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    receipt_date = models.DateField()
    client = models.ForeignKey('Customer', on_delete=models.CASCADE,null=True, blank=True)
    invoice = models.OneToOneField(InvoiceModel, on_delete=models.SET_NULL, null=True, blank=True)
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.CASCADE, null=True, blank=True)
    remark = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)


class Country(models.Model):
    name = models.CharField(max_length=100)
    flag = models.ImageField(upload_to='flags/', blank=True, null=True)

    def __str__(self):
        return self.name

class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name    
    
class Customer(models.Model):
    CUSTOMER_TYPES = [
        ('individual', 'Individual'),
        ('business', 'Business'),
    ]

    customer_type = models.CharField(max_length=10, choices=CUSTOMER_TYPES, default='individual')
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.CASCADE)
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField()
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    mobile = models.CharField(max_length=15)

    def __str__(self):
        if self.customer_type == 'individual':
            return f"{self.first_name} {self.last_name}"
        return self.company_name    


class TermsAndConditions(models.Model):
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    def str(self):
        return f"{self.title}"

class TermsAndConditionsPoint(models.Model):
    terms_and_conditions = models.ForeignKey(TermsAndConditions, on_delete=models.CASCADE)
    point = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    def str(self):
        return f"{self.point} - ({self.terms_and_conditions.title})"
    



class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    purchase_order_number = models.CharField(max_length=50, unique=True)
    purchase_order_date = models.DateField()
    contact_person_name = models.CharField(max_length=50)
    contact_person_number = models.CharField(max_length=50)
    quotation_number = models.CharField(max_length=50, blank=True, null=True)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True)
    terms_and_conditions = models.ForeignKey('TermsAndConditions', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.purchase_order_number
    

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Quantity * Unit Price
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Total + SGST + CGST


class MaterialReceive(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    material_receive_number = models.CharField(max_length=50, unique=True)
    received_date = models.DateField()
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, null=True, blank=True)


class MaterialReceiveItem(models.Model):
    material_receive = models.ForeignKey(MaterialReceive, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)





class Contract(models.Model):
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ContractSection(models.Model):
    contract = models.ForeignKey(Contract, related_name='sections', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)

    

    def __str__(self):
        return f'{self.contract.title} - {self.title}'


class ContractPoint(models.Model):
    section = models.ForeignKey(ContractSection, related_name='points', on_delete=models.CASCADE)
    points = models.TextField()

    

    def __str__(self):
        return self.points[:50]