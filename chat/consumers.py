from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.contrib.auth import get_user_model
from chat.models import Message, ChatRoom
from django.shortcuts import get_object_or_404
from asgiref.sync import sync_to_async

CustomUser = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Authenticate user
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return

        # Check room participation (async query)
        room = await sync_to_async(get_object_or_404, thread_sensitive=True)(
            ChatRoom, id=self.room_id, participants=user
        )
        if not room:
            await self.close()
            return

        # Join room group via Redis
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        content = text_data_json.get('content', '').strip()

        if not content:
            return

        # Save message to DB (async)
        user = self.scope['user']
        room = await sync_to_async(get_object_or_404, thread_sensitive=True)(
            ChatRoom, id=self.room_id
        )
        message = await sync_to_async(Message.objects.create)(
            room=room, sender=user, content=content
        )

        # Broadcast to room group via Redis
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'sender_id': user.id,
                'sender_name': f"{user.first_name} {user.last_name}",
                'content': content,
                'timestamp': message.timestamp.isoformat(),
                'is_read': False
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'is_read': event['is_read']
        }))