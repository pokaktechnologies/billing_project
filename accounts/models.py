from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now
from decimal import Decimal
from django_countries.fields import CountryField
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.db import models
from django.db.models import Sum

class CustomUserManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required")
        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email=self.normalize_email(email),
            **extra_fields
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
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)

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
    force_logout_time = models.DateTimeField(null=True, blank=True, default=None)
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def logout(self):
        """Force logout this user by updating last_logout."""
        self.last_logout = timezone.now()
        self.save(update_fields=['last_logout'])


    def __str__(self):
        return self.email


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.id} - {self.name}"


class StaffProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="staff_profile")
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    qulification = models.CharField(max_length=255, blank=True, null=True)
    staff_email = models.EmailField(blank=True, null=True)
    profile_image = models.ImageField(upload_to="staff/profile_images/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - ({self.user.first_name} {self.user.last_name})"

class JobDetail(models.Model):
    staff = models.OneToOneField(StaffProfile, on_delete=models.CASCADE, related_name="job_detail")
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    job_type = models.CharField(max_length=50, choices=[
        ("full_day", "Full Day"),
        ("part_time", "Part Time"),
        ("internship", "Internship"),
        ("contract", "Contract")
    ] , null=True, blank=True)
    signature_image = models.ImageField(upload_to="staff/signatures/", blank=True, null=True)
    role = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    status = models.CharField(max_length=50, choices=[
        ("active", "Active"),
        ("probation", "Probation"),
        ("resigned", "Resigned"),
        ("terminated", "Terminated"),
        ('inactive', 'Inactive'),
    ], default="active")

    def __str__(self):
        return f"{self.staff.user.email} - {self.role}"


class StaffDocument(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=100)  # e.g. "Aadhar", "Passport"
    file = models.FileField(upload_to="staff/documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.user.email} - {self.doc_type}"


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
    # stock = models.DecimalField(max_digits=10, decimal_places=2, default=0,blank=True, null=True)
    stock = models.IntegerField(default=0)  # Stock quantity
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')

    # NEW: tax setting
    tax_setting = models.ForeignKey(
        'finance.TaxSettings',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )



    # --------- TAX PROPERTIES ---------
    @property
    def sgst_pct(self):
        """
        Returns SGST percentage (half of GST rate).
        Safe even if tax_setting is None.
        """
        if not self.tax_setting:
            return Decimal("0.00")
        return self.tax_setting.rate / 2

    @property
    def cgst_pct(self):
        """
        Returns CGST percentage (half of GST rate).
        """
        if not self.tax_setting:
            return Decimal("0.00")
        return self.tax_setting.rate / 2
    
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
    payment_terms = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    def __str__(self):
        return f"{self.company_name or 'Unnamed'} - {self.contact_person_name or 'Unknown'}"



class DeliveryChallan(models.Model):
    customer_name = models.CharField(max_length=255)
    delivery_challan_number = models.CharField(max_length=50, unique=True)
    customer_note = models.TextField(blank=True)

    def __str__(self):
        return f"Delivery Challan {self.delivery_challan_number} - {self.customer_name}"  
    
class SalesPerson(models.Model):
    assigned_staff = models.OneToOneField(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='salespersons'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
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
    client = models.ForeignKey('Customer', on_delete=models.PROTECT, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT,null=True, blank=True)
    lead = models.OneToOneField('leads.Lead',on_delete=models.PROTECT,related_name='quotation', null=True,blank=True)
    quotation_number = models.CharField(max_length=50, unique=True)
    project_name = models.CharField(max_length=255, blank=True, null=True)
    quotation_date = models.DateField()
    delivery_address = models.TextField(max_length=100, blank=True )  
    delivery_location = models.TextField(max_length=100, blank=True)
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL, null=True, blank=True)
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
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
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
    customer = models.ForeignKey('Customer', on_delete=models.PROTECT)
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT,null=True, blank=True)
    sales_order_number = models.CharField(max_length=50, unique=True)
    sales_date = models.DateField()
    purchase_order_number = models.CharField(max_length=50, blank=True, null=True)
    remark = models.CharField(max_length=255, blank=True)
    delivery_location = models.CharField(max_length=255, blank=True)
    delivery_address = models.TextField(blank=True)
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL,  null=True, blank=True)
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
    product = models.ForeignKey('Product',  on_delete=models.PROTECT)
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
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT,null=True, blank=True)
    customer = models.ForeignKey('Customer', on_delete=models.PROTECT,null=True, blank=True)
    delivery_number = models.CharField(max_length=50, unique=True)
    delivery_date = models.DateField()
    sales_order = models.ForeignKey(SalesOrderModel, on_delete=models.PROTECT, related_name="deliveries")
    delivery_location = models.CharField(max_length=255, blank=True)
    delivery_address = models.TextField(blank=True)
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL,  null=True, blank=True)
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
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    # sales_order_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    delivered_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    returned_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def net_quantity(self):
        return self.delivered_quantity - self.returned_quantity

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
    INVOICE_TYPES = (
        ('client', 'Client'),
        ('intern', 'Intern'),
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPES,
        default='client'
    )

    # Intern reference
    intern = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="intern_invoices")
    # Course reference
    course = models.ForeignKey('internship.Course', on_delete=models.PROTECT, null=True, blank=True)

    
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT,null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    client = models.ForeignKey('Customer', on_delete=models.PROTECT,null=True, blank=True)
    sales_order = models.ForeignKey(SalesOrderModel, on_delete=models.PROTECT, null=True, blank=True)
    # delivery = models.ForeignKey(DeliveryFormModel, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL, null=True, blank=True)
    remark = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    is_receipted = models.BooleanField(default=False)
    class Meta:
        ordering = ["-created_at"]

    def recalculate_total(self):
        total = self.items.aggregate(
            total=Sum("sub_total")
        )["total"] or Decimal("0.00")

        self.invoice_grand_total = total
        self.save(update_fields=["invoice_grand_total"])

    def __str__(self):
        return f"{self.invoice_number} ({self.invoice_type})"
    
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(InvoiceModel, related_name='items', on_delete=models.CASCADE)
    # Product-based invoice item fields
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    # Keep delivery link for backward compatibility (optional)
    delivary = models.ManyToManyField(DeliveryFormModel, blank=True)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        self.sgst = (self.total * self.sgst_percentage) / Decimal("100")
        self.cgst = (self.total * self.cgst_percentage) / Decimal("100")
        self.sub_total = self.total + self.sgst + self.cgst

        super().save(*args, **kwargs)

        if self.invoice_id:
            self.invoice.recalculate_total()


class ReceiptModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT,null=True, blank=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    receipt_date = models.DateField()
    client = models.ForeignKey('Customer', on_delete=models.PROTECT,null=True, blank=True)
    invoice = models.ForeignKey(InvoiceModel, on_delete=models.PROTECT, null=True, blank=True)
    # termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL, null=True, blank=True)
    remark = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    cheque_number = models.CharField(max_length=50, blank=True, null=True)
    cheque_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    prepared_by = models.CharField(max_length=255, blank=True, null=True)
    recived_by = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)


class SalesReturnModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True)
    client = models.ForeignKey('Customer', on_delete=models.PROTECT)
    sales_return_number = models.CharField(max_length=50, unique=True)
    sales_order = models.ForeignKey(SalesOrderModel, on_delete=models.PROTECT)
    return_date = models.DateField()
    termsandconditions = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField()
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def update_grand_total(self):
        total = sum(item.sub_total for item in self.items.all())
        self.grand_total = total
        self.save(update_fields=["grand_total"])

    def __str__(self):
        return f"Sales Return {self.sales_return_number} - {self.client}"

class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(SalesReturnModel, on_delete=models.CASCADE, related_name='items')
    delivery_item = models.ForeignKey(DeliveryItem, on_delete=models.PROTECT) 
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Financial fields (auto-populated)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    
    # Calculated fields
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def clean(self):
        """Validate return quantity doesn't exceed available quantity"""
        if self.quantity > self.delivery_item.net_quantity:
            raise ValidationError(
                f"Cannot return {self.quantity}. Only {self.delivery_item.net_quantity} available"
            )
            
        if not self.delivery_item.delivery_form.is_invoiced:
            raise ValidationError("Cannot return from uninvoiced delivery")

    def save(self, *args, **kwargs):
        # Auto-populate from delivery item
        if not self.pk:  # Only on creation
            self.unit_price = self.delivery_item.unit_price
            self.sgst_percentage = self.delivery_item.sgst_percentage
            self.cgst_percentage = self.delivery_item.cgst_percentage
        
        # Calculate financials
        self.total = self.unit_price * self.quantity
        self.sgst = (self.sgst_percentage * self.total) / 100
        self.cgst = (self.cgst_percentage * self.total) / 100
        self.sub_total = self.total + self.sgst + self.cgst
        
        # Update delivery item's returned quantity
        if self.pk:
            old = SalesReturnItem.objects.get(pk=self.pk)
            delta = self.quantity - old.quantity
            self.delivery_item.returned_quantity += delta
        else:
            self.delivery_item.returned_quantity += self.quantity
        
        self.delivery_item.save()
        
        # Update inventory based on condition
        # self.delivery_item.product.quantity_in_stock += self.quantity
        # self.delivery_item.product.save()
        
        super().save(*args, **kwargs)
        self.sales_return.update_grand_total()

    def delete(self, *args, **kwargs):
        self.delivery_item.returned_quantity -= self.quantity
        self.delivery_item.save()
        print(f"Deleted Sales Return Item: {self.delivery_item.product.name} - {self.quantity}")
        super().delete(*args, **kwargs)
        self.sales_return.update_grand_total()
    
    def __str__(self):
        return f"{self.quantity} x {self.delivery_item.product.name}"




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
    address = models.TextField(blank=True, null=True)
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
    terms_and_conditions = models.ForeignKey('TermsAndConditions', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.purchase_order_number
    

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
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
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)





class Contract(models.Model):
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_template = models.BooleanField(default=False)

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
    


# models.py
class ModulePermission(models.Model):
    MODULE_CHOICES = [
        ("quotation", "Quotation"),
        ("sales_order", "Sales Order"),
        ("delivery", "Delivery"),
        ("client", "Client"),
        ("sales_person", "Sales Person"),
        ("setup", "Setup"),
        ("leads", "Leads"),
        ("leads_management", "Leads Management"),
        ("project_management", "Project Management"),
        ("supplier", "Supplier"),
        ("purchase", "Purchase"),
        ("material_receive", "Material Receive"),
        ("invoice", "Invoice"),
        ("receipt", "Receipt"),
        # ("sales_return", "Sales Return"),
        # ("stock", "Stock"),
        # ("expense", "Expense"),
        ("reports", "Reports"),
        ("sales_returns", "Sales Returns"),
        ("accounts", "Accounts"),
        # ("payments", "Payments"),
        ("products", "Products"),
        ('hr_section', "HR Section"),
        ('marketing', "Marketing"),
        ('certificate', "Certificate"),

        ('instructor', "Instructor"),
        ('intern', "Intern"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="module_permissions")
    module_name = models.CharField(max_length=50, choices=MODULE_CHOICES)

    class Meta:
        unique_together = ('user', 'module_name')

    def __str__(self):
        return f"{self.user.email} - {self.module_name}"
