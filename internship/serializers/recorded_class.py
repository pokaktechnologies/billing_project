from rest_framework import serializers
from ..models import RecordedClass, Course, Batch, Faculty


class RecordedClassSerializer(serializers.ModelSerializer):
    """
    Serializer for Admins and Faculties to list, create, and update recorded classes.
    """
    course_name = serializers.CharField(source="course.title", read_only=True)
    batch_name = serializers.CharField(source="batch.batch_number", read_only=True)
    faculty_name = serializers.SerializerMethodField(read_only=True)
    video_url = serializers.SerializerMethodField(read_only=True)
    thumbnail_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RecordedClass
        fields = [
            "id",
            "title",
            "description",
            "course",
            "course_name",
            "batch",
            "batch_name",
            "faculty",
            "faculty_name",
            "source_type",
            "video_file",
            "video_url",
            "external_url",
            "thumbnail",
            "thumbnail_url",
            "duration_seconds",
            "order",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "video_file": {"write_only": False, "required": False},
        }

    def get_faculty_name(self, obj):
        if obj.faculty:
            return obj.faculty.get_full_name()
        return None

    def get_video_url(self, obj):
        request = self.context.get("request")
        if obj.video_file:
            return request.build_absolute_uri(obj.video_file.url) if request else obj.video_file.url
        return obj.external_url

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        if obj.thumbnail:
            return request.build_absolute_uri(obj.thumbnail.url) if request else obj.thumbnail.url
        return None

    def validate(self, attrs):
        # Validate that if batch is provided, it belongs to the given course
        course = attrs.get("course") or (self.instance.course if self.instance else None)
        batch = attrs.get("batch") or (self.instance.batch if self.instance else None)

        if batch and course and batch.course_id != course.id:
            raise serializers.ValidationError({"batch": "Selected batch does not belong to the selected course."})

        # Ensure either video_file or external_url is provided when creating or if source requires it
        source_type = attrs.get("source_type") or (self.instance.source_type if self.instance else "upload")
        video_file = attrs.get("video_file")
        external_url = attrs.get("external_url")

        if not self.instance:
            if source_type == "upload" and not video_file and not attrs.get("external_url"):
                raise serializers.ValidationError({"video_file": "Video file is required for upload source."})
            if source_type == "external_url" and not external_url:
                raise serializers.ValidationError({"external_url": "External URL is required for external source."})

        return attrs


class StudentRecordedClassSerializer(serializers.ModelSerializer):
    """
    Read-only serializer tailored for enrolled students to stream recorded classes.
    """
    course_name = serializers.CharField(source="course.title", read_only=True)
    batch_name = serializers.CharField(source="batch.batch_number", read_only=True)
    faculty_name = serializers.SerializerMethodField(read_only=True)
    video_url = serializers.SerializerMethodField(read_only=True)
    thumbnail_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RecordedClass
        fields = [
            "id",
            "title",
            "description",
            "course",
            "course_name",
            "batch",
            "batch_name",
            "faculty_name",
            "video_url",
            "thumbnail_url",
            "duration_seconds",
            "order",
            "created_at",
        ]

    def get_faculty_name(self, obj):
        if obj.faculty:
            return obj.faculty.get_full_name()
        return None

    def get_video_url(self, obj):
        request = self.context.get("request")
        if obj.video_file:
            return request.build_absolute_uri(obj.video_file.url) if request else obj.video_file.url
        return obj.external_url

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        if obj.thumbnail:
            return request.build_absolute_uri(obj.thumbnail.url) if request else obj.thumbnail.url
        return None
