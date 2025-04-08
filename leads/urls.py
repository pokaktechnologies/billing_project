from django.urls import path
from .views import *

urlpatterns = [
    path('', LeadsView.as_view(), name='leads_view'),
    path('<int:pk>/', LeadDetailView.as_view(), name='lead_detail'),
]
