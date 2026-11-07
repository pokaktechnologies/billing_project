
from django.urls import path
from .consumers import LeadNotificationConsumer

websocket_urlpatterns = [
    path(
        "ws/lead-notifications/",
        LeadNotificationConsumer.as_asgi()
    ),
]
