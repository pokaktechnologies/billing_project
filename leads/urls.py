from django.urls import path
from .views.LeadsViews import *
from .views.MarketingViews import *

urlpatterns = [
    path('', LeadsView.as_view(), name='leads_view'),
    path('<int:pk>/', LeadDetailView.as_view(), name='lead_detail'),
    path('followup/', LeadsFollowUpView.as_view(), name='lead_followup'),
    path('search/', LeadSearchView.as_view(), name='lead_search'),
    path('no-quotation/', LeadsWithoutQuotationView.as_view(), name='leads-without-quotation'),
    path('meeting/', MeetingsView.as_view(), name='meeting_view'),
    path('meeting/<int:pk>/', MeetingDetailView.as_view(), name='meeting_detail'),
    path('meeting/search/', MeetingSearchView.as_view(), name='meeting_search'),
    path('meeting/reminder/', MeetingRemiderView.as_view(), name='meeting_reminder'),

    # marketing leads
    path('location/', LocationtView.as_view(), name='location_view'),
    path('location/<int:pk>/', LocationtDetailView.as_view(), name='location_detail'),
    path('source/', SourceAPIView.as_view(), name='source_view'),
    path('source/<int:pk>/', SourceDetailView.as_view(), name='source_detail'),
    path('category/', CategoryAPIView.as_view(), name='category_view'),
    path('category/<int:pk>/', CategoryDetailAPIView.as_view(), name='category_detail'),
    path('marketing-report/', MarketingReportAPIView.as_view(), name='marketing_report_view'),
    path('marketing-report/<int:pk>/', MarketingReportDetailAPIView.as_view(), name='marketing_report_detail'),
]
