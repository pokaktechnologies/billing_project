from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now
from decimal import Decimal


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
    product_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    product_description = models.TextField(blank=True)
    unit = models.CharField(max_length=50)  # Example: kg, liter, piece
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    # total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # def save(self, *args, **kwargs):
    #     # self.total_price = self.unit_price  # Set total_price same as unit_price
    #     super().save(*args, **kwargs)

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


        
class InvoiceOrder(models.Model):
    customer_name = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    terms = models.CharField(max_length=255, blank=True)
    due_date = models.DateField()
    salesperson = models.CharField(max_length=255)              
    subject = models.TextField(blank=True)
    attachments = models.URLField(blank=True)
    invoice_amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2,null=False, blank=False, default=1)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)  # New field

    
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
    
class SupplierPurchase(models.Model):
    supplier_name = models.CharField(max_length=255)
    purchase_number = models.CharField(max_length=50, unique=True, default='Unknown')
    date = models.DateField()
    product_name = models.CharField(max_length=255, default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    terms = models.CharField(max_length=255, blank=True)
    due_date = models.DateField()
    purchase_person = models.CharField(max_length=255, default='Unknown')
    subject = models.TextField(blank=True)
    add_stock = models.BooleanField(default=False)
    attachments = models.URLField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2,null=False, blank=False , default=1)

    def __str__(self):
        return f"Purchase {self.supplier_number} - {self.supplier_name}"        
    
class Supplier(models.Model):
    SUPPLIER_TYPE_CHOICES = [
        ('Business', 'Business'),
        ('Individual', 'Individual'),
    ]
    
    supplier_type = models.CharField(max_length=20, choices=SUPPLIER_TYPE_CHOICES)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    supplier_display_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    mobile = models.CharField(max_length=20)
    currency = models.CharField(max_length=10)
    payment_terms = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.supplier_display_name


class DeliveryChallan(models.Model):
    customer_name = models.CharField(max_length=255)
    delivery_challan_number = models.CharField(max_length=50, unique=True)
    customer_note = models.TextField(blank=True)

    def __str__(self):
        return f"Delivery Challan {self.delivery_challan_number} - {self.customer_name}"  
    
class SalesPerson(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    mobile = models.CharField(max_length=15, unique=True)
    incentive = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.display_name    
    
class QuotationOrderModel(models.Model):
    customer_name = models.CharField(max_length=255)
    quotation_number = models.CharField(max_length=50, unique=True)
    quotation_date = models.DateField()
    terms = models.CharField(max_length=255, blank=True)
    due_date = models.DateField()
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.CASCADE)  # Fetching from SalesPerson model
    email_id = models.EmailField(default=1)  # New field
    subject = models.TextField(blank=True)
    attachments = models.FileField(upload_to='quotations/', blank=True, null=True)  # File upload

    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def update_grand_total(self):
        """Recalculate grand total based on related QuotationItems."""
        total_amount = sum(item.sub_total for item in self.items.all())  # Sum of all items' sub_total
        self.grand_total = total_amount
        self.save(update_fields=["grand_total"])  # Save only the g

    def __str__(self):
        return f"Quotation {self.quotation_number} - {self.customer_name}"    
    

class QuotationItem(models.Model):
    quotation = models.ForeignKey(QuotationOrderModel, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # product_description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    # unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Auto-calculated field
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # quantity * unit_price
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% SGST
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% CGST
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # Total + SGST + CGST
    
    
    def save(self, *args, **kwargs):
        """Calculate and update total, SGST, CGST, and sub_total before saving."""
        self.total = self.product.unit_price * self.quantity
        self.sgst = (self.total * 9) / 100  # 9% SGST
        self.cgst = (self.total * 9) / 100  # 9% CGST
        self.sub_total = self.total + self.sgst + self.cgst
        super().save(*args, **kwargs)
        
        self.quotation.update_grand_total()

    def delete(self, *args, **kwargs):
        """Ensure grand total updates when an item is deleted."""
        super().delete(*args, **kwargs)
        self.quotation.update_grand_total()    

    def __str__(self):
        return self.product.name
       
    
class SalesOrderModel(models.Model):
        customer_name = models.CharField(max_length=255)
        sales_order_id = models.CharField(max_length=50, unique=True)  # Unique Sales Order ID
        sales_date = models.DateField()  # Sales Order Date
        purchase_order_number = models.CharField(max_length=50, blank=True, null=True)  # PO Number
        terms = models.CharField(max_length=255, blank=True)  # Payment terms
        due_date = models.DateField()  # Payment Due Date
        salesperson = models.ForeignKey(SalesPerson, on_delete=models.CASCADE)  # Salesperson responsible
        delivery_location = models.CharField(max_length=255, blank=True)  # Location for delivery
        delivery_address = models.TextField(blank=True)  # Full delivery address
        contact_person = models.CharField(max_length=255)  # Contact person for delivery
        mobile_number = models.CharField(max_length=15)  # Mobile number of contact person
        # attachments = models.FileField(upload_to='salesorder/', blank=True, null=True)  # File upload

        grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # Total sales amount

        def update_grand_total(self):
            """Recalculate grand total based on related SalesOrderItems."""
            total_amount = sum(item.sub_total for item in self.items.all())  # Sum of all items' sub_total
            self.grand_total = total_amount
            self.save(update_fields=["grand_total"])

        def __str__(self):
            return f"Sales Order {self.sales_order_id} - {self.customer_name}"


class SalesOrderItem(models.Model):
    sales_order = models.ForeignKey(SalesOrderModel, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # quantity * unit_price
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% SGST
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% CGST
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # Total + SGST + CGST

    def save(self, *args, **kwargs):
        """Calculate and update total, SGST, CGST, and sub_total before saving."""
        self.total = self.product.unit_price * self.quantity
        self.sgst = (self.total * Decimal("9")) / Decimal("100")  # 9% SGST
        self.cgst = (self.total * Decimal("9")) / Decimal("100")  # 9% CGST
        self.sub_total = self.total + self.sgst + self.cgst
        super().save(*args, **kwargs)

        self.sales_order.update_grand_total()

    def delete(self, *args, **kwargs):
        """Ensure grand total updates when an item is deleted."""
        super().delete(*args, **kwargs)
        self.sales_order.update_grand_total()

    def __str__(self):
        return self.product.name
    
    
class DeliveryFormModel(models.Model):
    customer_name = models.CharField(max_length=255)
    delivery_number = models.CharField(max_length=50, unique=True)  # Unique Delivery Number
    delivery_date = models.DateField()  # Delivery Date
    # sales_order_number = models.CharField(max_length=50, blank=True, null=True)  # Sales Order Number
    sales_order = models.ForeignKey(
        SalesOrderModel, on_delete=models.CASCADE, related_name="deliveries"
    )
    terms = models.CharField(max_length=255, blank=True)  # Payment terms
    due_date = models.DateField()  # Payment Due Date
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.CASCADE)  # Salesperson responsible
    delivery_location = models.CharField(max_length=255, blank=True)  # Location for delivery
    delivery_address = models.TextField(blank=True)  # Full delivery address
    contact_person = models.CharField(max_length=255)  # Contact person for delivery
    mobile_number = models.CharField(max_length=15)  # Mobile number of contact person
    
    # New Fields
    time = models.TimeField()  # Time of Delivery
    date = models.DateField()  # Date of Delivery

    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # Total delivery amount
    delivery_status = models.CharField(max_length=50, default="Pending")  


    def update_grand_total(self):
        """Recalculate grand total based on related DeliveryItems."""
        total_amount = sum(item.sub_total for item in self.items.all())  # Sum of all items' sub_total
        self.grand_total = total_amount
        self.save(update_fields=["grand_total"])

    def __str__(self):
        return f"Delivery {self.delivery_number} - {self.customer_name}"


class DeliveryItem(models.Model):
    delivery_form = models.ForeignKey(DeliveryFormModel, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    delivered_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Add this field
    status = models.CharField(max_length=50, default="Pending")  # Example status choices can be added

    
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # quantity * unit_price
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% SGST
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # 9% CGST
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)  # Total + SGST + CGST

    def save(self, *args, **kwargs):
        """Calculate and update total, SGST, CGST, and sub_total before saving."""
        self.total = self.product.unit_price * self.quantity
        self.sgst = (self.total * Decimal("9")) / Decimal("100")  # 9% SGST
        self.cgst = (self.total * Decimal("9")) / Decimal("100")  # 9% CGST
        self.sub_total = self.total + self.sgst + self.cgst
        super().save(*args, **kwargs)

        self.delivery_form.update_grand_total()

    def delete(self, *args, **kwargs):
        """Ensure grand total updates when an item is deleted."""
        super().delete(*args, **kwargs)
        self.delivery_form.update_grand_total()

    def __str__(self):
        return self.product.name    