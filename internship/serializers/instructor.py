from rest_framework import serializers
from internship.models import *
from accounts.models import StaffProfile
from accounts.serializers.user import *
from internship.serializers.intern import TaskSubmissionAttachmentSerializer
from .internship_admin import StudentSerializer


class SimpleStaffProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = ["id", "user_email", "full_name"]

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class CourseInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseInstallment
        fields = [
            "id",
            "amount",
            "due_days_after_enrollment",
        ]


class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True
    )
    installments = CourseInstallmentSerializer(
        many=True,
        required=False
    )

    sgst = serializers.SerializerMethodField()
    cgst = serializers.SerializerMethodField()
    total_tax_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "department",
            "department_name",
            "total_fee",
            # "number_of_installments",
            "installments",
            "created_at",
            "tax_settings",
            "sgst",
            "cgst",
            "total_tax_percentage",
        ]
        read_only_fields = ["created_at", "sgst", "cgst", "total_tax_percentage"]


    # ---------- TAX LOGIC ----------
    def get_sgst(self, obj):
        if not obj.tax_settings:
            return 0
        return obj.tax_settings.rate / 2

    def get_cgst(self, obj):
        if not obj.tax_settings:
            return 0
        return obj.tax_settings.rate / 2
    
    def get_total_tax_percentage(self, obj):
        if not obj.tax_settings:
            return 0
        return obj.tax_settings.rate
    def validate(self, data):
        installments = data.get("installments", [])
        total_fee = data.get("total_fee", getattr(self.instance, "total_fee", None))

        if installments:
            total = sum(i["amount"] for i in installments)

            if total != total_fee:
                raise serializers.ValidationError(
                    "Sum of installment amounts must equal total_fee."
                )

            if self.instance is None:
                expected_count = data.get("number_of_installments")
            else:
                expected_count = data.get(
                    "number_of_installments",
                    self.instance.number_of_installments
                )

            if len(installments) != expected_count:
                raise serializers.ValidationError(
                    "Installment count must match number_of_installments."
                )

        return data

    def create(self, validated_data):
        installments_data = validated_data.pop("installments", [])
        course = Course.objects.create(**validated_data)

        for inst in installments_data:
            CourseInstallment.objects.create(
                course=course,
                **inst
            )

        return course

    def update(self, instance, validated_data):
        installments_data = validated_data.pop("installments", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if installments_data is not None:
            # Hard reset installments (simple & predictable)
            instance.installments.all().delete()

            for inst in installments_data:
                CourseInstallment.objects.create(
                    course=instance,
                    **inst
                )

        return instance


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

        #  Missing staff
        missing = [sid for sid in staff_ids if sid not in found_ids]
        if missing:
            raise serializers.ValidationError({
                "staff_ids": f"Staff ids not found: {missing}"
            })

        #  Staff already assigned to ANY course
        already_assigned = AssignedStaffCourse.objects.filter(
            staff__in=staff_qs
        ).values_list("staff_id", flat=True)

        already_assigned = list(set(already_assigned))
        if already_assigned:
            raise serializers.ValidationError({
                "staff_ids": f"These staff are already assigned to another course: {already_assigned}"
            })

        #  Validate internship job_type
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
        batch = attrs.get("batch") or getattr(self.instance, "batch", None)

        if not batch:
            raise serializers.ValidationError("Batch is required for study material.")

        if not file and not url:
            raise serializers.ValidationError("Either file or url is required.")
        return attrs


class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ['id', 'file']


class TaskAssignmentSerializer(serializers.ModelSerializer):
    staff = SimpleStaffProfileSerializer(read_only=True)
    student = StudentSerializer(read_only=True)

    class Meta:
        model = TaskAssignment
        fields = "__all__"
from internship.models import Task
class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    assigned_to_ids = serializers.SerializerMethodField()
    total_student_count = serializers.SerializerMethodField()

    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description',
            'start_date', 'due_date', 'status', 'course',
            'assigned_to', 'attachments',
            'total_student_count', 'assigned_to_ids'
        ]

    # ===== STATUS =====
    def get_status(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        student_id = request.query_params.get("student")
        if not student_id:
            return None

        assignment = obj.assignments.filter(student_id=student_id).first()
        return assignment.status if assignment else None

    # ===== COUNT =====
    def get_total_student_count(self, obj):
        return obj.assigned_to.count()

    # ===== IDS =====
    def get_assigned_to_ids(self, obj):
        return list(obj.assigned_to.values_list('id', flat=True))

    # ===== CREATE =====
    def create(self, validated_data):
        student_ids = validated_data.pop('assigned_to', [])
        request = self.context['request']
        files = request.FILES.getlist('files')

        course = validated_data.get("course")
        if not course:
            raise serializers.ValidationError({"course": "Course is required."})

        # ✅ validate students belong to course (adjust if your model differs)
        valid_students = Student.objects.filter(
            id__in=student_ids,
            course=course
        )

        valid_student_ids = valid_students.values_list("id", flat=True)
        invalid_students = set(student_ids) - set(valid_student_ids)

        if invalid_students:
            raise serializers.ValidationError({
                "assigned_to": f"Invalid student IDs: {list(invalid_students)}"
            })

        # create task
        task = Task.objects.create(**validated_data)

        # create assignments
        for student_id in valid_student_ids:
            TaskAssignment.objects.create(
                task=task,
                student_id=student_id
            )

        # attachments
        for file in files:
            TaskAttachment.objects.create(task=task, file=file)

        return task

    # ===== UPDATE =====
    def update(self, instance, validated_data):
        student_ids = validated_data.pop('assigned_to', None)
        request = self.context['request']
        files = request.FILES.getlist('files')

        # update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # update assignments
        if student_ids is not None:
            course = instance.course

            valid_students = Student.objects.filter(
                id__in=student_ids,
                course=course
            )

            valid_student_ids = valid_students.values_list("id", flat=True)
            invalid_students = set(student_ids) - set(valid_student_ids)

            if invalid_students:
                raise serializers.ValidationError({
                    "assigned_to": f"Invalid student IDs: {list(invalid_students)}"
                })

            # clear old assignments
            TaskAssignment.objects.filter(task=instance).delete()

            # create new ones
            for student_id in valid_student_ids:
                TaskAssignment.objects.create(
                    task=instance,
                    student_id=student_id
                )

        # new attachments
        for file in files:
            TaskAttachment.objects.create(task=instance, file=file)

        return instance

class InstructorTaskDetailSerializer(serializers.ModelSerializer):
    staff_assignments = TaskAssignmentSerializer(
        many=True,
        read_only=True,
        source='assignments'   # <-- this is the fix
    )
    attachments = TaskAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'start_date', 'due_date',
            'course', 'attachments', 'staff_assignments'
        ]



from rest_framework import serializers
from django.utils import timezone

class InstructorSubmissionSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='assignment.task.title', read_only=True)
    status = serializers.CharField(source='assignment.status', read_only=True)
    student = serializers.SerializerMethodField()
    due_date = serializers.DateField(source='assignment.task.due_date', read_only=True)

    class Meta:
        model = TaskSubmission
        fields = [
            "id",
            "title",
            "student",
            "assignment",
            "submitted_at",
            "link",
            "response",
            "instructor_feedback",
            "reviewed_at",
            "due_date",
            "status",
        ]

    def get_student(self, obj):
        student = obj.assignment.student
        if student and student.profile and student.profile.user:
            user = student.profile.user
            return f"{user.first_name} {user.last_name}"
        return None
class InstructorSubmissionDetailSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='assignment.task.title', read_only=True)
    description = serializers.CharField(source='assignment.task.description', read_only=True)
    status = serializers.CharField(source='assignment.status', read_only=True)
    student = serializers.SerializerMethodField()
    due_date = serializers.DateField(source='assignment.task.due_date', read_only=True)

    attachments = TaskSubmissionAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = TaskSubmission
        fields = [
            "id",
            "title",
            "description",
            "student",
            "status",
            "assignment",
            "link",
            "response",
            "instructor_feedback",
            "attachments",
            "submitted_at",
            "reviewed_at",
            "due_date",
        ]

    def get_student(self, obj):
        student = obj.assignment.student
        if student and student.profile and student.profile.user:
            user = student.profile.user
            return f"{user.first_name} {user.last_name}"
        return None
class InstructorSubmissionReviewSerializer(serializers.ModelSerializer):
    # Map status and revision_due_date to the related assignment fields
    status = serializers.ChoiceField(
        choices=[("revision_required", "revision_required"), ("completed", "completed")],
        required=True,
        source="assignment.status",
    )
    revision_due_date = serializers.DateField(required=False, allow_null=True, source="assignment.revision_due_date")

    class Meta:
        model = TaskSubmission
        fields = [
            "id",
            "instructor_feedback",
            "reviewed_at",
            "status",
            "revision_due_date",
        ]

    def update(self, instance, validated_data):
        # Pop nested assignment data (if present)
        assignment_data = validated_data.pop("assignment", {})

        # update task submission fields
        instance.instructor_feedback = validated_data.get("instructor_feedback", instance.instructor_feedback)
        # ensure reviewed_at is a timezone-aware datetime (DateTimeField expects datetime)
        instance.reviewed_at = validated_data.get("reviewed_at", timezone.now())
        instance.save()

        # now update assignment if assignment data provided
        assignment = instance.assignment
        if assignment_data:
            new_status = assignment_data.get("status")
            if new_status is not None:
                assignment.status = new_status
                if new_status == "revision_required":
                    assignment.revision_due_date = assignment_data.get("revision_due_date", None)
                else:
                    assignment.revision_due_date = None
                assignment.save()

        return instance



class InternListSerializer(serializers.ModelSerializer):
    job_detail = JobDetailSerializer(read_only=True)
    tasks = serializers.SerializerMethodField()
    intern_name = serializers.SerializerMethodField()
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            'id',
            'intern_name',
            'email',
            'staff_email',
            'job_detail',
            'tasks',
        ]

    def get_intern_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    def get_tasks(self, obj):
        total = obj.taskassignment_set.count()
        completed = obj.taskassignment_set.filter(status='completed').count()
        return {
            "completed": completed,
            "total": total
        }


class InternProfileSerializer(serializers.ModelSerializer):
    job_detail = JobDetailSerializer(read_only=True)
    documents = StaffDocumentSerializer(many=True, read_only=True)
    intern_name = serializers.SerializerMethodField()
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = StaffProfile
        fields = ['id','intern_name', 'email', 'phone_number', 'qulification', 'staff_email', 'profile_image', 'date_of_birth', 'address', 'job_detail', 'documents']

    def get_intern_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
