from django.urls import path
from .views.views import *
from accounts.views.user import  *

from .views.SearchViews import *

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify_otp'),
    path('admin/forgot-password/request-otp/', AdminForgotPasswordRequestView.as_view(), name='admin-forgot-password-request'),
    path('admin/forgot-password/verify-otp/', AdminForgotPasswordVerifyView.as_view(), name='admin-forgot-password-verify'),
    path('admin/forgot-password/reset-password/', AdminForgotPasswordResetView.as_view(), name='admin-forgot-password-reset'),
    path('profile/', ProfileAPIView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('client/token/', ClientTokenObtainPairView.as_view(), name='client_token_obtain_pair'),
    path('admin/token/', SuperuserTokenObtainPairView.as_view(), name='superuser_token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('create-staff/', CreateStaffWithPermissionsView.as_view(), name="create-staff"),
    path('create-staff/<int:staff_id>/', CreateStaffWithPermissionsView.as_view(), name="create-staff"),
    # path('admin/assign-permissions/', AssignPermissionView.as_view()),y
    # path('admin/staffs/', ListStaffView.as_view()),
    # path('admin/staffs/<int:staff_id>/', ListStaffView.as_view()),
    path("staff/<int:id>/update/", UpdateStaffUserView.as_view(), name="update_staff_user"),
    path("job-detail/<int:id>/update/", UpdateJobDetailView.as_view(), name="update_job_detail"),

    path("staff-documents/create/", StaffDocumentCreateView.as_view(), name="staff-document-create"),
    path("staff-documents/<int:id>/update/", StaffDocumentUpdateView.as_view(), name="staffdocument-update"),
    path("staff-documents/<int:id>/delete/", StaffDocumentDeleteView.as_view(), name="staff-document-delete"),
    path("user/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("users/<int:user_id>/module-permissions/update/", UserModulePermissionUpdateView.as_view(), name="user-module-permissions-update"),


    path('user/modules/', StaffModulesView.as_view()),
    path('user/modules/all/', StaffModulesListView.as_view()),

    path('departments/', DepartmentView.as_view()),
    path('departments/<int:department_id>/', DepartmentView.as_view()),


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


    path('invoice/', InvoiceAPI.as_view(), name='invoice'),
    path("invoice/<int:ioid>/", InvoiceDetailAPI.as_view()),
    path('invoice/pending/', PendingInvoiceListView.as_view()),
    path('invoice/client/<int:client_id>/', InvoicesByClientAPI.as_view()),
    path('invoice/intern/<int:intern_id>/', InvoicesByInternAPI.as_view()),
    
    path('receipts/', ReceiptView.as_view(), name='receipt'),
    path('receipts/<int:rec_id>/', ReceiptView.as_view(), name='receipt'),
    path('print-receipts/<int:rec_id>/', PrintReceiptView.as_view(), name='print_receipt'),

    path('sales-returns/',SalesReturnAPI.as_view(), name='sales-returns-list'),
    path('sales-returns/<int:return_id>/',SalesReturnDetailAPI.as_view(),name='sales-returns-detail'),
    path('print-sales-returns/<int:return_id>/', SalesReturnPrint.as_view(), name='print_sales_return'),
    path('sales-returns/client/<int:client_id>/', SalesOrderByClient.as_view(), name='sales_order_by_client'),
    path('delivery-orders/sales-order/<int:sales_order_id>/', DelivaryOrderBySalesOrder.as_view(), name='delivery_order_by_sales_order'),

    path('orders/generate-number/', OrderNumberGeneratorView.as_view(), name='order_number_generator'),

    #------------------
    # REPORTS APIS
    #------------------
    path('reports/sales-summary/',SalesReportSummaryView.as_view(), name='sales_report_summary'),
    path('reports/sales-by-client/',SalesReportByClientView.as_view(), name='sales_report_by_client'),
    path('reports/sales-by-items/',SalesReportByItemsView.as_view(), name='sales_report_by_items'),
    path('reports/sales-by-salesperson/',SalesReportBySalespersonView.as_view(), name='sales_report_by_salesperson'),
    path('reports/sales-by-category/',SalesReportByCategoryView.as_view(), name='sales_report_by_category'),

    path('reports/quotation/', QuotationReportView.as_view(), name='quotation_report'),
    path('reports/invoice/', InvoiceReportView.as_view(), name='invoice_report'),

    
    path('quotations/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/<int:qid>/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/<int:qid>/<int:pid>/', QuotationOrderAPI.as_view(), name='quotation-items-detail'),
    path('quotations/search/', QuatationSearchView.as_view(), name='quotation-items-detail'),
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

    path('staff/info/', StaffPersonalInfoView.as_view(), name='staff-personal-info'),
    path('staff/attendance/',StaffPersonalAttendanceView.as_view(), name='staff-attendance-info'),

    path('unassigned-staff/', UnassignedStaffListView.as_view(), name='unassigned-staff-list'),


    ## DASHBOARD URLS
    path('dashboard/developer/', DeveloperDashboardView.as_view(), name='developers-dashboard'),
    path('dashboard/designer/', GraphicDesignerDashboardView.as_view(), name='admin-dashboard'),

]
