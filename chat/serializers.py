from rest_framework import serializers
from django.contrib.auth import get_user_model
from chat.models import ChatRoom, Message
from accounts.models import StaffProfile, JobDetail
from django.utils import timezone
from datetime import datetime

CustomUser = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source='staff_profile.job_detail.department.name', default='')
    role = serializers.CharField(source='staff_profile.job_detail.role', default='')
    employee_id = serializers.CharField(source='staff_profile.job_detail.employee_id', default='')
    phone = serializers.CharField(source='staff_profile.phone_number', default='')
    location = serializers.CharField(source='staff_profile.address', default='')
    join_date = serializers.DateField(source='staff_profile.job_detail.start_date', default=None)
    tenure = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='staff_profile.profile_image', read_only=True, default=None)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'department', 'role', 'employee_id', 
                  'phone', 'location', 'join_date', 'tenure', 'avatar']

    def get_tenure(self, obj):
        staff_profile = getattr(obj, 'staff_profile', None)
        job_detail = getattr(staff_profile, 'job_detail', None)

        if job_detail and job_detail.start_date:
            start_date = job_detail.start_date
            diff = timezone.now().date() - start_date
            years = diff.days // 365
            months = (diff.days % 365) // 30
            return f"{years} years, {months} months"
        return "N/A"


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'sender_name', 'content', 'timestamp', 'is_read']
        read_only_fields = ['timestamp', 'is_read']

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}"

class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'description', 'type', 'participants', 'created_at', 'updated_at', 
                  'last_message', 'unread_count']
        read_only_fields = ['created_at', 'updated_at']

    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        return MessageSerializer(last_msg).data if last_msg else None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0

    def create(self, validated_data):
        participants_data = self.context.get('view').request.data.get('participants', [])
        room = ChatRoom.objects.create(**validated_data)
        if participants_data:
            users = CustomUser.objects.filter(id__in=participants_data)
            room.participants.set(users)
        return room

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        participants_data = self.context.get('view').request.data.get('participants', [])
        if participants_data:
            users = CustomUser.objects.filter(id__in=participants_data)
            instance.participants.set(users)
        instance.save()
        return instance