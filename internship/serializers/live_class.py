import uuid
from rest_framework import serializers
from ..models import LiveClass, LiveClassAttendance, Course, Batch, Faculty


class FacultySimpleSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    email = serializers.CharField(source='user.user.email', read_only=True)

    class Meta:
        model = Faculty
        fields = ['id', 'full_name', 'email']


class CourseSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title']


class BatchSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['id', 'batch_number']


class LiveClassSerializer(serializers.ModelSerializer):
    course_details = CourseSimpleSerializer(source='course', read_only=True)
    batch_details = BatchSimpleSerializer(source='batch', read_only=True)
    faculty_details = FacultySimpleSerializer(source='faculty', read_only=True)

    class Meta:
        model = LiveClass
        fields = [
            'id',
            'title',
            'description',
            'course',
            'course_details',
            'batch',
            'batch_details',
            'faculty',
            'faculty_details',
            'room_name',
            'status',
            'scheduled_start_time',
            'scheduled_end_time',
            'actual_start_time',
            'actual_end_time',
            'is_recording_enabled',
            'recorded_class',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'room_name',
            'actual_start_time',
            'actual_end_time',
            'recorded_class',
            'created_at',
            'updated_at',
        ]

    def create(self, validated_data):
        # Auto-generate a unique room_name if not provided
        if not validated_data.get('room_name'):
            course_id = validated_data.get('course').id if validated_data.get('course') else 'x'
            batch_id = validated_data.get('batch').id if validated_data.get('batch') else 'all'
            short_uuid = uuid.uuid4().hex[:8]
            validated_data['room_name'] = f"room_c{course_id}_b{batch_id}_{short_uuid}"
        return super().create(validated_data)


class StudentLiveClassSerializer(serializers.ModelSerializer):
    course_details = CourseSimpleSerializer(source='course', read_only=True)
    batch_details = BatchSimpleSerializer(source='batch', read_only=True)
    faculty_details = FacultySimpleSerializer(source='faculty', read_only=True)

    class Meta:
        model = LiveClass
        fields = [
            'id',
            'title',
            'description',
            'course_details',
            'batch_details',
            'faculty_details',
            'room_name',
            'status',
            'scheduled_start_time',
            'scheduled_end_time',
            'actual_start_time',
            'is_recording_enabled',
        ]
        read_only_fields = fields


class LiveClassAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id_code = serializers.CharField(source='student.student_id', read_only=True)

    class Meta:
        model = LiveClassAttendance
        fields = [
            'id',
            'live_class',
            'student',
            'student_name',
            'student_id_code',
            'joined_at',
            'left_at',
            'duration_seconds',
        ]
        read_only_fields = ['id', 'joined_at']
