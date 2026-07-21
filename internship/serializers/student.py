from rest_framework import serializers
from ..models import Student



class StudentProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="profile.user.first_name", read_only=True)
    last_name = serializers.CharField(source="profile.user.last_name", read_only=True)
    email = serializers.EmailField(source="profile.user.email", read_only=True)
    phone = serializers.CharField(source="profile.phone", read_only=True)

    center = serializers.StringRelatedField()
    course = serializers.StringRelatedField()
    batch = serializers.StringRelatedField()
    payment_type = serializers.StringRelatedField()
    councellor = serializers.StringRelatedField()

    class Meta:
        model = Student
        fields = [
            "student_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "center",
            "course",
            "batch",
            "payment_type",
            "start_date",
            "status",
            "is_active",
            "councellor",
            "created_at",
        ]