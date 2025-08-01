from django.urls import path
from .views import *

urlpatterns = [
    path('', LeadsView.as_view(), name='leads_view'),
    path('<int:pk>/', LeadDetailView.as_view(), name='lead_detail'),
    path('followup/', LeadsFollowUpView.as_view(), name='lead_followup'),
    path('search/', LeadSearchView.as_view(), name='lead_search'),
    path('meeting/', MeetingsView.as_view(), name='meeting_view'),
    path('meeting/<int:pk>/', MeetingDetailView.as_view(), name='meeting_detail'),
    path('meeting/search/', MeetingSearchView.as_view(), name='meeting_search'),
    path('meeting/reminder/', MeetingRemiderView.as_view(), name='meeting_reminder'),
]
