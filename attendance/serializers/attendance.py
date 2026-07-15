from rest_framework import serializers
from ..models import DailyAttendance, AttendanceSession

class AttendanceSessionSerializer(serializers.ModelSerializer):
    session_duration = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = ['id', 'session', 'status', 'login_time', 'logout_time', 'session_duration']

    def get_session_duration(self, obj):
        return obj.session_duration()


class DailyAttendanceSerializer(serializers.ModelSerializer):
    sessions = AttendanceSessionSerializer(many=True, read_only=True)
    
    first_name = serializers.CharField(source='staff.user.first_name', read_only=True)
    last_name = serializers.CharField(source='staff.user.last_name', read_only=True)
    employee_id = serializers.CharField(source='staff.job_detail.employee_id', read_only=True)
    department = serializers.CharField(source='staff.job_detail.department.name', read_only=True)
    class Meta:
        model = DailyAttendance
        fields = ['id', 'staff','first_name', 'last_name','employee_id','department', 'date', 'total_working_hours', 'status', 'sessions']

    def update(self, instance, validated_data):
        instance.status = validated_data.get("status", instance.status)
        instance.save(update_fields=["status", "updated_at"])
        return instance


class DailyAttendanceSessionDetailSerializer(serializers.ModelSerializer):
    sessions = AttendanceSessionSerializer(many=True, read_only=True)
    class Meta:
        model = DailyAttendance
        fields = ['staff', 'id', 'date', 'total_working_hours', 'status', 'sessions']
