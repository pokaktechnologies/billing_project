from django.urls import path
from .views import SignupView, OTPVerificationView, UserSettingView,GettingStartedView,ProductListCreateAPIView,ProductUpdateDeleteAPIView, HomePageView, HelpLinkView, NotificationView, UserSettingView, FeedbackView, CreateSalesOrderAPI,SalesOrderListAPI,CreateQuotationOrderAPI, QuotationOrderListAPI, CreateInvoiceOrderAPI,InvoiceOrderListAPI,CreateDeliveryOrderAPI,DeliveryOrderListAPI, CreateSupplierPurchaseAPI,SupplierPurchaseListAPI,CreateSupplierAPI,SupplierListAPI,CreateDeliveryChallanAPI,DeliveryChallanListAPI,UpdateDeliveryChallanAPI

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
    path('products/<int:pk>/', ProductUpdateDeleteAPIView.as_view(), name='product-update-delete'),
    path('sales-orders/', CreateSalesOrderAPI.as_view(), name='create_sales_order'),
    path('get-sales-orders/', SalesOrderListAPI.as_view(), name='sales_order_list'),
    path('quotation-orders/', CreateQuotationOrderAPI.as_view(), name='create_quotation_order'),
    path('get-quotation-orders/', QuotationOrderListAPI.as_view(), name='quotation_order_list'),
    path('invoice-orders/', CreateInvoiceOrderAPI.as_view(), name='create_invoice_order'),
    path('get-invoice-orders/', InvoiceOrderListAPI.as_view(), name='invoice_order_list'),
    path('delivery-orders/', CreateDeliveryOrderAPI.as_view(), name='create_delivery_order'),
    path('get-delivery-orders/', DeliveryOrderListAPI.as_view(), name='delivery_order_list'),
    path('create-purchase/', CreateSupplierPurchaseAPI.as_view(), name='create_supplier_purchase'),
    path('list-purchase/', SupplierPurchaseListAPI.as_view(), name='supplier_purchase_list'),
    path('suppliers/', CreateSupplierAPI.as_view(), name='create_supplier'),
    path('get-suppliers/', SupplierListAPI.as_view(), name='supplier_list'),
    path('create-delivery-challan/', CreateDeliveryChallanAPI.as_view(), name='create_delivery_challan'),
    path('list-delivery-challans/', DeliveryChallanListAPI.as_view(), name='list_delivery_challans'),
    path('update-delivery-challan/<int:pk>/', UpdateDeliveryChallanAPI.as_view(), name='update_delivery_challan'),
]
