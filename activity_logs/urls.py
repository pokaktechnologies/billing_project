from django.urls import path
from . import views


urlpatterns = [
    path('activity-logs/', views.ActivityLogListView.as_view(), name='activity-log-list'),
]