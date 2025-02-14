from django.contrib import admin
from .models import Product,SalesPerson  # Import your model

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'name', 'unit_price', 'unit')  # Display these fields in the admin panel
    search_fields = ('product_code', 'name')  # Add search functionality
    
    def has_delete_permission(self, request, obj=None):
        return True  # Ensure delet
# Register your models here.

@admin.register(SalesPerson)
class SalesPersonAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'first_name', 'last_name', 'email', 'phone', 'mobile', 'incentive')  
    search_fields = ('display_name', 'email', 'phone', 'mobile')  
    list_filter = ('incentive',)  # Optional: Filter by incentive
    ordering = ('display_name',)  # Orders by display_name
    
    def has_delete_permission(self, request, obj=None):
        return True  # Ensure delet