"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

# core/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# Set up Django FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()  # Must come before any Django model imports!

# Now import Django stuff
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs

# Import your routing
from chat import routing as chat_routing
from attendance import routing as attendance_routing

# JWT Auth Middleware
@database_sync_to_async
def get_user_from_token(token_key):
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        validated_token = JWTAuthentication().get_validated_token(token_key)
        return JWTAuthentication().get_user(validated_token)
    except:
        return AnonymousUser()

class QueryParamTokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)

# Final ASGI app
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": QueryParamTokenAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                attendance_routing.websocket_urlpatterns +
                chat_routing.websocket_urlpatterns
            )
        )
    ),
})