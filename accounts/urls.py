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
    
    path('delivery-orders/', DeliveryFormAPI.as_view(), name='create_delivery_order'),
     path('delivery-orders/<int:did>/', DeliveryFormAPI.as_view(), name='create_delivery_order'),

    # path('quotation-orders/', CreateQuotationOrderAPI.as_view(), name='create_quotation_order'),
    # path('get-quotation-orders/', QuotationOrderListAPI.as_view(), name='quotation_order_list'),
    # path('quotation-update-orders/<pk>/', QuotationOrderUpdateAPI.as_view(), name='quotation_order_list'),
    # path('quotation-delete-orders/<pk>/', QuotationOrderDeleteAPI.as_view(), name='quotation_order_list'),
    # path('quotations/', QuotationOrderAPIView.as_view(), name='quotations-list'),
    # path('quotations/<int:pk>/', QuotationOrderAPIView.as_view(), name='quotations-detail'), 
    # path('quotations/<int:quotation_pk>/items/', QuotationItemAPIView.as_view(), name='quotation-items-list'),
    # path('quotations/<int:quotation_pk>/items/<int:item_pk>/', QuotationItemAPIView.as_view(), name='quotation-items-detail'),
    
    # path('quotations/', QuotationOrderAPIView.as_view(), name='quotations-list'),
    # path('quotations/<int:pk>/', QuotationOrderAPIView.as_view(), name='quotations-detail'),
    
    # path('quotations/<int:quotation_pk>/items/', QuotationItemAPIView.as_view(), name='quotation-items-list'),
    # path('quotations/<int:quotation_pk>/items/<int:item_pk>/', QuotationItemAPIView.as_view(), name='quotation-items-detail'),
    
        
    # path('quotations/<int:quotation_pk>/items/', QuotationItemAPIView.as_view(), name='quotation-items-list'),
    # path('quotations/<int:quotation_pk>/items/<int:item_pk>/', QuotationItemAPIView.as_view(), name='quotation-items-detail'),
    
    path('quotations/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/<int:qid>/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
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
    


]
