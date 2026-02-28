from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ActivityLog
from .serializers import ActivityLogSerializer

# Create your views here.


# Activity Log List View

class ActivityLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    # required_module = 'activity_log'
    serializer_class = ActivityLogSerializer
    queryset = ActivityLog.objects.all().order_by('-timestamp')


