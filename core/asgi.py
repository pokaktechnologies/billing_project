"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from attendance import routing as attendance_routing  # 👈 import app routes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Django ASGI app
django_asgi_app = get_asgi_application()

# Main ASGI application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            attendance_routing.websocket_urlpatterns  # 👈 include attendance routes
        )
    ),
})

