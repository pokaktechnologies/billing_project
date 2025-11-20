from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import *



class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']

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
    modules = serializers.ListField(
        child=serializers.ChoiceField(choices=ModulePermission.MODULE_CHOICES),
        allow_empty=False
    )

    def create(self, validated_data):
        email = validated_data["email"]
        first_name = validated_data.get("first_name")
        last_name = validated_data.get("last_name")
        password = validated_data["password"]
        modules = validated_data["modules"]

        # Create user
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        user.is_staff = True  # Mark as staff if needed
        user.save()

        # Remove existing permissions
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
    


#  for get
from rest_framework import serializers

class StaffDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffDocument
        fields = ['id', 'doc_type', 'file']

class JobDetailSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source='department.name', default=None)

    class Meta:
        model = JobDetail
        fields = ['id','employee_id', 'department', 'job_type','signature_image', 'role', 'salary', 'start_date', 'status']

class StaffProfileSerializer(serializers.ModelSerializer):
    job_detail = JobDetailSerializer(read_only=True)
    documents = StaffDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = StaffProfile
        fields = ['id','phone_number', 'staff_email', 'profile_image', 'date_of_birth', 'address', 'job_detail', 'documents']

class StaffUserSerializer(serializers.ModelSerializer):
    profile = StaffProfileSerializer(source='staff_profile', read_only=True)
    modules = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'modules', 'profile']

    def get_modules(self, obj):
        return list(obj.module_permissions.values_list('module_name', flat=True))



#  update  

class StaffProfileUpdateSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = StaffProfile
        fields = ["phone_number", "staff_email", "profile_image", "date_of_birth", "address"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.profile_image:
            request = self.context.get("request")
            data["profile_image"] = request.build_absolute_uri(instance.profile_image.url) if request else instance.profile_image.url
        return data


class StaffUserUpdateSerializer(serializers.ModelSerializer):
    staff_profile = StaffProfileUpdateSerializer()

    class Meta:
        model = CustomUser
        fields = ["email", "first_name", "last_name", "staff_profile"]

    def update(self, instance, validated_data):
        # Update CustomUser fields
        instance.email = validated_data.get("email", instance.email)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.save()

        # Update StaffProfile
        staff_profile_data = validated_data.pop("staff_profile", None)
        if staff_profile_data:
            staff_profile = instance.staff_profile
            for attr, value in staff_profile_data.items():
                setattr(staff_profile, attr, value)
            staff_profile.save()

        return instance

    def validate_email(self, value):
        user_id = self.instance.id if self.instance else None
        if CustomUser.objects.exclude(id=user_id).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class JobDetailUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDetail
        fields = ["employee_id", "department", "job_type", "signature_image", "role", "salary", "start_date", "status"]

class StaffDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffDocument
        fields = "__all__"
        read_only_fields = ["uploaded_at"]


class ModulePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePermission
        fields = ['module_name']



class ChangePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_email(self, value):
        try:
            user = CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        self.context['target_user'] = user
        return value


class AdminForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        # Ensure this is an admin/is_superuser 
        if not user.is_superuser:
            raise serializers.ValidationError("Password reset via this endpoint is allowed for admin/is_superuser users only.")
        self.context['target_user'] = user
        return value


class AdminForgotPasswordVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        if not user.is_superuser:
            raise serializers.ValidationError({"email": "This action is allowed for admin/is_superuser users only."})
        # Basic OTP match (no expiry enforcement here to match existing project patterns)
        if not user.otp or user.otp != otp:
            raise serializers.ValidationError({"otp": "Invalid OTP."})
        self.context['target_user'] = user
        return attrs


class AdminForgotPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        if not user.is_superuser:
            raise serializers.ValidationError({"email": "This action is allowed for admin/is_superuser users only."})
        if not user.otp or user.otp != otp:
            raise serializers.ValidationError({"otp": "Invalid OTP."})
        if not user.is_otp_verified:
            raise serializers.ValidationError({"otp": "OTP not verified. Please verify OTP before resetting password."})
        self.context['target_user'] = user
        return attrs
    
class StaffPersonalInfoSerializer(serializers.ModelSerializer):
    profile = StaffProfileSerializer(source='staff_profile', read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'profile']

