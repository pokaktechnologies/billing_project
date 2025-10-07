from rest_framework import serializers
from .models import DailyAttendance, AttendanceSession
from accounts.models import JobDetail

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


class DailyAttendanceSessionDetailSerializer(serializers.ModelSerializer):
    sessions = AttendanceSessionSerializer(many=True, read_only=True)
    class Meta:
        model = DailyAttendance
        fields = ['staff', 'id', 'date', 'total_working_hours', 'status', 'sessions']

class DailyAttendanceEmployeeViewSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='staff.user.first_name', read_only=True)
    last_name = serializers.CharField(source='staff.user.last_name', read_only=True)
    department = serializers.CharField(source='staff.job_detail.department.name', read_only=True)

    class Meta:
        model = JobDetail
        fields = ['id', 'staff','first_name', 'last_name','employee_id', 'department', 'role']