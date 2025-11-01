from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ChatRoomViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'chats', ChatRoomViewSet, basename='chat')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'messages/<int:room_id>/',
        MessageViewSet.as_view({
            'get': 'list',      # Load message history
            'post': 'create'    # Send new message
        }),
        name='message-list-create'
    ),
]