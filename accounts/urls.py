from django.urls import path
from .views import *

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify_otp'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('getting-started/', GettingStartedView.as_view(), name='getting_started'),
    path('homepage/', HomePageView.as_view(), name='homepage'),
    path('help-links/', HelpLinkView.as_view(), name='help'),
    path('notifications/', NotificationView.as_view(), name='notifications'),   
    path('usersettings/', UserSettingView.as_view(), name='user_setting_list'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),
    path('products/', ProductListCreateAPIView.as_view(), name='product-list-create'),
    path('products/<int:product_id>/', ProductDetailAPI.as_view(), name='product-update-delete'),
    # path('sales-orders/', CreateSalesOrderAPI.as_view(), name='create_sales_order'),
    path('sales-orders/', SalesOrderAPI.as_view(), name='sales_order_list'),
    path('sales-orders/<int:sid>/', SalesOrderAPI.as_view(), name='sales_order_list'),
    path('sales-orders/<int:sid>/<int:pid>/', SalesOrderAPI.as_view(), name='sales_order_list'),
    path('sales-orders/<int:sid>/items/', SalesOrderItemsList.as_view(), name='sales_order_items_list'),
    path('sales-orders/not-delivered/', SalesOrderByNotDelivered.as_view(), name='sales_order_not_delivered'),
    path('print-sales-orders/<int:sid>/', PrintSalesOrderAPI.as_view(), name='print_sales_order'),
    
    path('countries/', CountryView.as_view(), name='get_states'),
    path('states/', StateView.as_view(), name='get_cities'),

    
    path('delivery-orders/', DeliveryFormAPI.as_view(), name='create_delivery_order'),
     path('delivery-orders/<int:did>/', DeliveryFormAPI.as_view(), name='create_delivery_order'),


    
    path('quotations/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/<int:qid>/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/<int:qid>/<int:pid>/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    # path('quotations/<int:qid>/items/', QuotationItemUpdateView.as_view(), name='quotation-items-list'),
    # path('quotations/<int:qid>/items/<int:item_id>/', QuotationItemUpdateView.as_view(), name='quotation-item-detail'),
  
#   path('quotations/<int:qid>/<int:pid>/', 
        #  QuotationItemUpdateView.as_view(), 
        #  name='quotation-item-update'),

    path('print-quotations/<int:qid>/', PrintQuotationAPI.as_view(), name='quotation-items-detail'),
    path('invoice-orders/', CreateInvoiceOrderAPI.as_view(), name='create_invoice_order'),
    path('get-invoice-orders/', InvoiceOrderListAPI.as_view(), name='invoice_order_list'),

    path('get-delivery-orders/', DeliveryOrderListAPI.as_view(), name='delivery_order_list'),
    path('create-purchase/', CreateSupplierPurchaseAPI.as_view(), name='create_supplier_purchase'),
    path('list-purchase/', SupplierPurchaseListAPI.as_view(), name='supplier_purchase_list'),
    path('suppliers/', CreateSupplierAPI.as_view(), name='create_supplier'),
    path('get-suppliers/', SupplierListAPI.as_view(), name='supplier_list'),
    path('create-delivery-challan/', CreateDeliveryChallanAPI.as_view(), name='create_delivery_challan'),
    path('list-delivery-challans/', DeliveryChallanListAPI.as_view(), name='list_delivery_challans'),
    path('update-delivery-challan/<int:pk>/', UpdateDeliveryChallanAPI.as_view(), name='update_delivery_challan'),
    path('salespersons/', SalesPersonListCreateAPIView.as_view(), name='salespersons_list'),
    path('salespersons/<int:pk>/', SalesPersonListCreateAPIView.as_view(), name='salespersons'),
    
    path('customers/', CustomerListCreateAPIView.as_view(), name='customer-list-create'),
    path('customers/<int:pk>/', CustomerListCreateAPIView.as_view(), name='customer-detail'),
    path('category/', CategoryListCreateAPIView.as_view(), name='category-list-create'),
    path('category/<int:pk>/', CategoryListCreateAPIView.as_view(), name='category-detail'),
    
    path('units/', UnitAPIView.as_view(), name='unit-list-create'),  # List and Create
    path('units/<int:pk>/', UnitAPIView.as_view(), name='unit-detail'),  # Retrieve, Update, Delete
    path('bank-accounts/', BankAccountAPI.as_view(), name='bank_account_list'),  # Get all, Post new
    path('bank-accounts/<int:account_id>/', BankAccountAPI.as_view(), name='bank_account_detail'),  # Get, Put, Delete
    
    path('terms/', TermsAndConditionsAPI.as_view()),
    path('terms/<int:pk>/', TermsAndConditionsAPI.as_view()),
    path('terms-points/', TermsAndConditionsPointAPI.as_view()),
    path('terms-points/<int:pk>/', TermsAndConditionsPointAPI.as_view()),

]
