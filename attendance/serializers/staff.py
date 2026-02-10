from rest_framework import serializers
from accounts.models import JobDetail

class DailyAttendanceEmployeeViewSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='staff.user.first_name', read_only=True)
    last_name = serializers.CharField(source='staff.user.last_name', read_only=True)
    department = serializers.CharField(source='staff.job_detail.department.name', read_only=True)

    class Meta:
        model = JobDetail
        fields = ['id', 'staff','first_name', 'last_name','employee_id', 'department', 'role']
