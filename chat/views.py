from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from chat.models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer, UserSerializer
from accounts.models import JobDetail, CustomUser
from django.shortcuts import get_object_or_404

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomUser.objects.filter(staff_profile__job_detail__status='active').distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        search_query = request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(staff_profile__job_detail__employee_id__icontains=search_query) |
                Q(staff_profile__job_detail__role__icontains=search_query) |
                Q(staff_profile__job_detail__department__name__icontains=search_query)
            ).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(participants=self.request.user).distinct()

    def create(self, request, *args, **kwargs):
        participants = request.data.get('participants', [])
        if not participants or self.request.user.id not in participants:
            return Response({"error": "Invalid participants list"}, status=status.HTTP_400_BAD_REQUEST)
        if len(participants) == 2 and 'type' in request.data and request.data['type'] == 'one_to_one':
            user1, user2 = CustomUser.objects.filter(id__in=participants)
            room = ChatRoom.get_or_create_one_to_one(user1, user2)
            serializer = self.get_serializer(room)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if self.request.user not in instance.participants.all():
            return Response({"error": "Not a participant"}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class MessageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        room = get_object_or_404(ChatRoom, id=room_id, participants=self.request.user)
        return Message.objects.filter(room=room).order_by('timestamp')

    def create(self, request, room_id=None):
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        serializer = self.serializer_class(data={
            'room': room.id,
            'sender': request.user.id,
            'content': request.data.get('content')
        })
        serializer.is_valid(raise_exception=True)
        message = serializer.save(room=room, sender=request.user)

        # Return full message + room ID for frontend
        return Response({
            'id': message.id,
            'room': room.id,
            'sender': message.sender.id,
            'sender_name': f"{message.sender.first_name} {message.sender.last_name}",
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'is_read': message.is_read
        }, status=status.HTTP_201_CREATED)

    def list(self, request, room_id=None):
        queryset = self.get_queryset()
    
    # Auto mark as read when user views the chat
        Message.objects.filter(
        room__id=room_id,
        is_read=False
        ).exclude(sender=request.user).update(is_read=True)

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
