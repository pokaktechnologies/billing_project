from django.urls import path
from .consumers import ActivityLogConsumer


websocket_urlpatterns = [
        path('ws/activity-log/', ActivityLogConsumer.as_asgi()),
]