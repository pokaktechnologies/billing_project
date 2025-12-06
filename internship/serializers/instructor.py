from rest_framework import serializers
from internship.models import *
from accounts.models import StaffProfile
from accounts.serializers.user import *

class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Course
        fields = ["id", "title", "description", "department", "department_name"]


class AssignedStaffCourseSerializer(serializers.ModelSerializer):
    staff = serializers.IntegerField(source="staff.id", read_only=True)
    staff_email = serializers.CharField(source="staff.user.email", read_only=True)
    staff_full_name = serializers.SerializerMethodField()
    course = serializers.IntegerField(source="course.id", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = AssignedStaffCourse
        fields = [
            "id",
            "staff",
            "staff_email",
            "staff_full_name",
            "course",
            "course_title",
            "assigned_date",
        ]

    def get_staff_full_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"




# ====== BULK CREATE SERIALIZER ======
class AssignedStaffCourseCreateSerializer(serializers.Serializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    staff_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    def validate(self, attrs):
        course = attrs["course"]
        staff_ids = attrs["staff_ids"]

        staff_qs = StaffProfile.objects.filter(id__in=staff_ids)
        found_ids = set(staff_qs.values_list("id", flat=True))

        # Missing staff
        missing = [sid for sid in staff_ids if sid not in found_ids]
        if missing:
            raise serializers.ValidationError({
                "staff_ids": f"Staff ids not found: {missing}"
            })

        # Staff already assigned
        existing = AssignedStaffCourse.objects.filter(
            course=course, staff__in=staff_qs
        ).values_list("staff_id", flat=True)

        existing_list = list(existing)
        if existing_list:
            raise serializers.ValidationError({
                "staff_ids": f"Staff already assigned to the course: {existing_list}"
            })

        # Validate job_type
        invalid = []
        for s in staff_qs:
            jd = getattr(s, "job_detail", None)
            if not jd or (jd.job_type or "").lower() != "internship":
                invalid.append(s.id)

        if invalid:
            raise serializers.ValidationError({
                "staff_ids": f"These staff are not internship staff: {invalid}"
            })

        attrs["staff_qs"] = staff_qs
        return attrs


    def create(self, validated_data):
        course = validated_data["course"]
        staff_qs = validated_data["staff_qs"]

        existing = AssignedStaffCourse.objects.filter(
            course=course, staff__in=staff_qs
        ).values_list("staff_id", flat=True)

        to_create = [
            AssignedStaffCourse(course=course, staff=sp)
            for sp in staff_qs if sp.id not in existing
        ]

        return AssignedStaffCourse.objects.bulk_create(to_create)


# ====== DETAIL SERIALIZER (GET/PUT/PATCH/DELETE) ======
class AssignedStaffCourseDetailSerializer(serializers.ModelSerializer):
    Staff_email = serializers.CharField(source="staff.user.email", read_only=True)
    course_details = CourseSerializer(source="course", read_only=True)
    
    class Meta:
        model = AssignedStaffCourse
        fields = ["id", "staff", "course", "assigned_date", "Staff_email", "course_details"]

    def validate(self, attrs):
        staff = attrs.get("staff", getattr(self.instance, "staff", None))
        course = attrs.get("course", getattr(self.instance, "course", None))

        jd = getattr(staff, "job_detail", None)
        if not jd or (jd.job_type or "").lower() != "internship":
            raise serializers.ValidationError({
                "staff": "Staff must have job_type 'internship'."
            })

        qs = AssignedStaffCourse.objects.filter(staff=staff, course=course)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "This staff is already assigned."
            )
        return attrs

# ====== Study Material Serializer ======
    
class StudyMaterialSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudyMaterial
        fields = "__all__"

    def validate(self, attrs):
        file = attrs.get("file")
        url = attrs.get("url")

        if not file and not url:
            raise serializers.ValidationError("Either file or url is required.")
        return attrs
