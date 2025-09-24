from rest_framework import serializers
from .models import DailyAttendance, AttendanceSession

class AttendanceSessionSerializer(serializers.ModelSerializer):
    session_duration = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = ['id', 'session', 'status', 'login_time', 'logout_time', 'session_duration']

    def get_session_duration(self, obj):
        return obj.session_duration()


class DailyAttendanceSerializer(serializers.ModelSerializer):
    sessions = AttendanceSessionSerializer(many=True, read_only=True)

    class Meta:
        model = DailyAttendance
        fields = ['id', 'staff', 'date', 'total_working_hours', 'status', 'sessions']
