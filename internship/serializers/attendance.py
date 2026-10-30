from rest_framework import serializers
from django.utils import timezone
from ..models import (
    ClassAttendanceSession,
    StudentAttendanceRecord,
    Section,
    Student,
    StudentCourseEnrollment,
)


class StudentAttendanceRosterItemSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_code = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField(allow_null=True)
    profile_image = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(
        choices=StudentAttendanceRecord.STATUS_CHOICES,
        default='present'
    )
    remarks = serializers.CharField(allow_blank=True, required=False, default="")


class SectionAttendanceRosterSerializer(serializers.Serializer):
    section_id = serializers.IntegerField()
    class_id = serializers.IntegerField()
    class_name = serializers.CharField()
    center_id = serializers.IntegerField(allow_null=True)
    center_name = serializers.CharField(allow_null=True)
    batch_id = serializers.IntegerField()
    batch_number = serializers.CharField()
    course_id = serializers.IntegerField()
    course_title = serializers.CharField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    date = serializers.DateField()
    is_marked = serializers.BooleanField()
    session_id = serializers.IntegerField(allow_null=True)
    topic_covered = serializers.CharField(allow_null=True, allow_blank=True)
    notes = serializers.CharField(allow_null=True, allow_blank=True)
    marked_by = serializers.CharField(allow_null=True)
    marked_at = serializers.DateTimeField(allow_null=True)
    total_enrolled = serializers.IntegerField()
    students = StudentAttendanceRosterItemSerializer(many=True)


class StudentAttendanceRecordInputSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=StudentAttendanceRecord.STATUS_CHOICES,
        default='present'
    )
    remarks = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default=""
    )


class BulkAttendanceSubmitSerializer(serializers.Serializer):
    date = serializers.DateField(default=timezone.now().date)
    topic_covered = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default=""
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )
    records = serializers.ListField(
        child=StudentAttendanceRecordInputSerializer(),
        allow_empty=False
    )

    def validate_records(self, value):
        student_ids = [item['student_id'] for item in value]
        if len(student_ids) != len(set(student_ids)):
            raise serializers.ValidationError("Duplicate student entries found in attendance records.")
        return value


class ClassAttendanceSessionHistorySerializer(serializers.ModelSerializer):
    faculty_name = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()
    present_count = serializers.SerializerMethodField()
    absent_count = serializers.SerializerMethodField()
    leave_count = serializers.SerializerMethodField()
    late_count = serializers.SerializerMethodField()
    attendance_rate = serializers.SerializerMethodField()

    class Meta:
        model = ClassAttendanceSession
        fields = [
            'id',
            'date',
            'topic_covered',
            'notes',
            'faculty_name',
            'total_students',
            'present_count',
            'absent_count',
            'leave_count',
            'late_count',
            'attendance_rate',
            'created_at',
            'updated_at',
        ]

    def get_faculty_name(self, obj):
        if obj.faculty:
            return obj.faculty.get_full_name()
        return "Unknown"

    def get_total_students(self, obj):
        return obj.records.count()

    def get_present_count(self, obj):
        return obj.records.filter(status='present').count()

    def get_absent_count(self, obj):
        return obj.records.filter(status='absent').count()

    def get_leave_count(self, obj):
        return obj.records.filter(status='leave').count()

    def get_late_count(self, obj):
        return obj.records.filter(status='late').count()

    def get_attendance_rate(self, obj):
        total = obj.records.count()
        if total == 0:
            return 0.0
        present = obj.records.filter(status__in=['present', 'late']).count()
        return round((present / total) * 100, 1)


class StudentAttendanceDetailItemSerializer(serializers.ModelSerializer):
    date = serializers.DateField(source='session.date', read_only=True)
    topic_covered = serializers.CharField(source='session.topic_covered', read_only=True)
    class_name = serializers.CharField(source='session.section.class_obj.name', read_only=True)
    batch_number = serializers.CharField(source='session.section.batch.batch_number', read_only=True)
    course_title = serializers.CharField(source='session.section.batch.course.title', read_only=True)
    start_time = serializers.TimeField(source='session.section.start_time', read_only=True)
    end_time = serializers.TimeField(source='session.section.end_time', read_only=True)

    class Meta:
        model = StudentAttendanceRecord
        fields = [
            'id',
            'date',
            'class_name',
            'batch_number',
            'course_title',
            'start_time',
            'end_time',
            'status',
            'topic_covered',
            'remarks',
        ]
