from django.db import models
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

CustomUser = get_user_model()

class ChatRoom(models.Model):
    TYPE_CHOICES = (
        ('one_to_one', 'One-to-One'),
        ('group', 'Group'),
    )
    name = models.CharField(max_length=255, blank=True, null=True)  # Only for groups
    description = models.TextField(blank=True, null=True)  # Optional for groups
    participants = models.ManyToManyField(CustomUser, related_name='chat_rooms')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='group')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"Chat with {self.participants.first().email}"

    def get_unread_count(self, user):
        """Count unread messages for a specific user in this room."""
        return self.messages.filter(is_read=False, sender_id=user.id).count()

    def get_last_message(self):
        """Get the most recent message."""
        return self.messages.order_by('-timestamp').first()

    @classmethod
    def get_or_create_one_to_one(cls, user1, user2):
        """Get existing 1:1 room or create new, avoiding duplicates."""
        rooms = cls.objects.filter(type='one_to_one', participants=user1).filter(
            Q(participants=user2)
        ).distinct()
        if rooms.exists():
            return rooms.first()
        room = cls.objects.create(type='one_to_one')
        room.participants.add(user1, user2)
        return room

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.email} in {self.room}: {self.content[:20]}"

    class Meta:
        ordering = ['timestamp']
