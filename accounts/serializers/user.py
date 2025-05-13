from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import *



class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email']