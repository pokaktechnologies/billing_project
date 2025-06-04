from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import *



class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email']


class AssignPermissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    modules = serializers.ListField(child=serializers.ChoiceField(choices=ModulePermission.MODULE_CHOICES))

    def validate_user_id(self, value):
        if not CustomUser.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid user ID.")
        return value

    def create(self, validated_data):
        user = CustomUser.objects.get(id=validated_data['user_id'])
        modules = validated_data['modules']

        # Clear old permissions
        ModulePermission.objects.filter(user=user).delete()

        # Assign new permissions
        ModulePermission.objects.bulk_create([
            ModulePermission(user=user, module_name=module) for module in modules
        ])
        return validated_data
    


class CreateUserWithPermissionsSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    modules = serializers.ListField(child=serializers.ChoiceField(choices=ModulePermission.MODULE_CHOICES), allow_empty=False)

    def create(self, validated_data):
        email = validated_data["email"]
        first_name = validated_data.get("first_name")
        last_name = validated_data.get("last_name")
        password = validated_data["password"]
        modules = validated_data["modules"]

        # Create user
        user = CustomUser.objects.create_user(email=email, password=password, first_name=first_name, last_name=last_name)
        user.is_staff = True  # Mark as staff if needed
        user.save()

        # Assign permissions
        # ModulePermission.objects.bulk_create(user=user, module_name=modules)
        ModulePermission.objects.filter(user=user).delete()

        # Assign new permissions
        ModulePermission.objects.bulk_create([
            ModulePermission(user=user, module_name=module) for module in modules
        ])

        return user
    
    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value