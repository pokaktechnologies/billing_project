from django.urls import path
from .views import *

urlpatterns = [
    path('enquiry/', EnquiryCreateView.as_view(), name='enquiry'),
    path('enquiry/<int:pk>/', EnquiryDetailView.as_view(), name='enquiry_detail'),
    path('enquiry/<int:pk>/status/', EnquiryStatusUpdateView.as_view(), name='enquiry_status_update'),
    path('enquiry/statistics/', EnquiryStatisticsView.as_view(), name='enquiry_statistics'),
    path('enquiry/search/', SearchEnquiryView.as_view(), name='enquiry_search'),
]
