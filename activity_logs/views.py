from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ActivityLog
from .serializers import ActivityLogSerializer, ActivityLogCreateSerializer

# Create your views here.


# Activity Log List View

class ActivityLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    # required_module = 'activity_log'
    serializer_class = ActivityLogSerializer
    queryset = ActivityLog.objects.all().order_by('-timestamp')


class ActivityLogCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityLogCreateSerializer

    def perform_create(self, serializer):
        log = serializer.save(user=self.request.user)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "activity_logs",
            {
                "type": "send_log",
                "data": {
                    "id": log.id,
                    "user": str(log.user),
                    "action": log.action,
                    "model": log.model_name,
                    "description": log.description,
                    "time": str(log.timestamp)
                }
            }
        )
