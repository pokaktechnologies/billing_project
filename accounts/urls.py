from django.urls import path
from .views.views import *
from accounts.views.user import  (
    ProfileAPIView,
    AssignPermissionView,
    UserModulesView,
    CreateStaffWithPermissionsView
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify_otp'),
    path('profile/', ProfileAPIView.as_view()),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('create-staff/', CreateStaffWithPermissionsView.as_view(), name="create-staff"),
    path('admin/assign-permissions/', AssignPermissionView.as_view()),
    path('user/modules/', UserModulesView.as_view()),


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
    path('sales-orders/not-delivered/<int:customer_id>/', SalesOrderByNotDelivered.as_view(), name='sales_order_not_delivered'),
    path('sales-orders/is-invoiced/<int:customer_id>/', SalesOrderByInvoiced.as_view(), name='sales_order_is_invoiced'),
    path('print-sales-orders/<int:sid>/', PrintSalesOrderAPI.as_view(), name='print_sales_order'),
    
    path('countries/', CountryView.as_view(), name='get_states'),
    path('states/', StateView.as_view(), name='get_cities'),

    
    path('delivery-orders/', DeliveryFormAPI.as_view(), name='create_delivery_order'),
    path('delivery-orders/<int:did>/', DeliveryFormAPI.as_view(), name='create_delivery_order'),
    path('print-delivery-orders/<int:did>/', PrintDeliveryOrderAPI.as_view(), name='print_delivery_order'),
    path('delivery-orders/is_invoiced/<int:sid>/', DeliveryOrderIsInvoiced.as_view(), name='delivery_order_is_invoiced'),
    path('delivery-orders/items/', DelivaryOrderItemsList.as_view(), name='delivery_order_items_list'),

    path('invoice-orders/', InvoiceOrderAPI.as_view(), name='invoice-order'),
    path('invoice-orders/<int:ioid>/', InvoiceOrderAPI.as_view(), name='invoice-order'),
    path('print-invoice-orders/<int:ioid>/', PrintInvoiceView.as_view(), name='print_invoice_order'),

    path('receipts/', ReceiptView.as_view(), name='receipt'),
    path('receipts/<int:rec_id>/', ReceiptView.as_view(), name='receipt'),
    path('print-receipts/<int:rec_id>/', PrintReceiptView.as_view(), name='print_receipt'),

    path('orders/generate-number/', OrderNumberGeneratorView.as_view(), name='order_number_generator'),

    path('reports/sales-by-client/',SalesReportByClientView.as_view(), name='sales_report_by_client'),
    path('reports/sales-by-items/',SalesReportByItemsView.as_view(), name='sales_report_by_items'),
    path('reports/sales-by-salesperson/',SalesReportBySalespersonView.as_view(), name='sales_report_by_salesperson'),
    path('reports/sales-by-category/',SalesReportByCategoryView.as_view(), name='sales_report_by_category'),

    
    path('quotations/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/<int:qid>/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/<int:qid>/<int:pid>/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    # path('quotations/<int:qid>/items/', QuotationItemUpdateView.as_view(), name='quotation-items-list'),
    # path('quotations/<int:qid>/items/<int:item_id>/', QuotationItemUpdateView.as_view(), name='quotation-item-detail'),
  
#   path('quotations/<int:qid>/<int:pid>/', 
        #  QuotationItemUpdateView.as_view(), 
        #  name='quotation-item-update'),

    path('print-quotations/<int:qid>/', PrintQuotationAPI.as_view(), name='quotation-items-detail'),

    path('get-delivery-orders/', DeliveryOrderListAPI.as_view(), name='delivery_order_list'),
    # path('create-purchase/', CreateSupplierPurchaseAPI.as_view(), name='create_supplier_purchase'),
    # path('list-purchase/', SupplierPurchaseListAPI.as_view(), name='supplier_purchase_list'),
    path('suppliers/',SupplierAPIView.as_view(), name='supplier'),
    path('suppliers/<int:pk>/', SupplierAPIView.as_view(), name='supplier_detail'),
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
    path('terms-points/<int:term_id>/terms/',  ListTermsandConditionsPointsAPI.as_view()),

    path('purchase-orders/', PurchaseOrderAPIView.as_view(), name='purchase-order-list-create'),
    path('purchase-orders/<int:pk>/', PurchaseOrderAPIView.as_view(), name='purchase-order-retrieve-update-destroy'),

    path('material-receive/', MaterialReceiveAPIView.as_view(), name='purchase-order-list-create'),
    path('material-receive/<int:pk>/', MaterialReceiveAPIView.as_view(), name='purchase-order-retrieve-update-destroy'),

    path('contracts/', ContractListCreateAPIView.as_view()),
    path('contracts/<int:contract_id>/', ContractListCreateAPIView.as_view()),
    path('contracts/<int:contract_id>/detail/', ContractDetailViewApiView.as_view()),

    # Sections
    path('contracts/<int:contract_id>/sections/', ContractSectionListCreateAPIView.as_view()),
    path('contracts/<int:contract_id>/sections/<int:section_id>/', ContractSectionListCreateAPIView.as_view()),

    # Points
    path('contracts/<int:contract_id>/sections/<int:section_id>/points/', ContractPointListCreateAPIView.as_view()),
    path('contracts/<int:contract_id>/sections/<int:section_id>/points/<int:point_id>/', ContractPointListCreateAPIView.as_view()),
]
