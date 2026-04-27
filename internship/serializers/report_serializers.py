from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils.timezone import now
from rest_framework import serializers

from accounts.models import StaffProfile, SalesPerson
from internship.models import Batch, Center, Course, Student, TaskSubmission, AssignedStaffCourse, CoursePayment, TaskAssignment, Faculty, InstallmentItem
from internship.serializers.internship_admin import InstallmentPlanSerializer
from internship.utils import (
    get_installment_due_date_for_staff,
    get_next_unpaid_installment_item,
)


# report based on task
class TaskReportSerializer(serializers.ModelSerializer):
    intern_id = serializers.IntegerField(source="staff.id", read_only=True)
    task_id = serializers.IntegerField(source="task.id")
    task_title = serializers.CharField(source="task.title")
    description = serializers.CharField(source="task.description")
    assigned_to = serializers.SerializerMethodField()
    course = serializers.CharField(source="task.course.title")
    assigned_date = serializers.DateTimeField(source="assigned_at")
    due_date = serializers.DateField(source="task.due_date")
    status = serializers.CharField()

    class Meta:
        model = TaskAssignment

        fields = [
            "intern_id",
            "task_id",
            "task_title",
            "description",
            "assigned_to",
            "course",
            "assigned_date",
            "due_date",
            "status",
        ]

    def get_assigned_to(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"


# report based on per intern task performance
class InternTaskPerformanceReportSerializer(serializers.ModelSerializer):
    intern_id = serializers.IntegerField(source="staff.id")
    intern_name = serializers.SerializerMethodField()
    course = serializers.CharField(source="course.title")
    total_tasks = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    pending = serializers.SerializerMethodField()
    avg_score = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    feedback = serializers.SerializerMethodField()

    class Meta:
        model = AssignedStaffCourse

        fields = [
            "intern_id",
            "intern_name",
            "course",
            "total_tasks",
            "completed",
            "pending",
            "avg_score",
            "completion_rate",
            "feedback",
        ]

    def get_intern_name(self, obj):

        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"

    def get_assignments(self, obj):

        return TaskAssignment.objects.filter(
            staff=obj.staff,
            task__course=obj.course
        )

    def get_total_tasks(self, obj):

        return self.get_assignments(obj).count()

    def get_completed(self, obj):

        return self.get_assignments(obj).filter(status="completed").count()

    def get_pending(self, obj):
        return self.get_assignments(obj).filter(
            status__in=["pending", "submitted", "revision_required"]
        ).count()

    def get_completion_rate(self, obj):
        total = self.get_total_tasks(obj)
        completed = self.get_completed(obj)

        if total == 0:
            return 0
        return round((completed / total) * 100, 2)

    # Placeholder logic (until you implement scoring system)
    def get_avg_score(self, obj):
        return self.get_completion_rate(obj)

    def get_feedback(self, obj):
        rate = self.get_completion_rate(obj)

        if rate >= 90:
            return "Outstanding"
        elif rate >= 80:
            return "Excellent"
        elif rate >= 70:
            return "Very Good"
        elif rate >= 60:
            return "Good"
        else:
            return "Needs Improvement"


# reports based on task submission reports
class TaskSubmissionReportSerializer(serializers.ModelSerializer):
    intern_id = serializers.IntegerField(source="assignment.staff.id", read_only=True)
    task_title = serializers.CharField(source="assignment.task.title", read_only=True)
    intern_name = serializers.SerializerMethodField()
    submission_date = serializers.DateTimeField(source="submitted_at", read_only=True)
    due_date = serializers.DateField(source="assignment.task.due_date", read_only=True)
    status = serializers.CharField(source="assignment.status", read_only=True)
    feedback = serializers.CharField(source="instructor_feedback", read_only=True)
    review_date = serializers.DateTimeField(source="reviewed_at", read_only=True)

    class Meta:
        model = TaskSubmission

        fields = [
            "intern_id",
            "task_title",
            "intern_name",
            "submission_date",
            "due_date",
            "status",
            "feedback",
            "review_date",
        ]

    def get_intern_name(self, obj):
        staff = obj.assignment.staff
        return f"{staff.user.first_name} {staff.user.last_name}"


# report based on intern payment details
class InternPaymentSummaryReportSerializer(serializers.ModelSerializer):
    intern_id = serializers.IntegerField(source="staff.id", read_only=True)
    intern_name = serializers.SerializerMethodField()
    course_id = serializers.IntegerField(source="course.id")
    course_title = serializers.CharField(source="course.title")
    total_fee = serializers.DecimalField(source="course.total_fee", max_digits=10, decimal_places=2)
    paid_amount = serializers.SerializerMethodField()
    pending_amount = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()

    class Meta:
        model = AssignedStaffCourse
        fields = [
            "intern_id",
            "intern_name",
            "course_id",
            "course_title",
            "total_fee",
            "paid_amount",
            "pending_amount",
            "payment_status",
            "next_due_date",
            "overdue_days",
        ]
    def get_intern_name(self, obj):

        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"

    def get_paid_amount(self, obj):

        total = CoursePayment.objects.filter(
            student__profile=obj.staff,
            installments__plan__course=obj.course
        ).aggregate(
            total=Sum("amount_paid")
        )["total"]

        return total or 0

    def get_pending_amount(self, obj):

        paid = self.get_paid_amount(obj)

        return obj.course.total_fee - paid

    def get_payment_status(self, obj):

        pending = self.get_pending_amount(obj)

        if pending <= 0:
            return "Fully Paid"

        next_due = self.get_next_due_date(obj)

        if next_due and next_due < now().date():
            return "Overdue"

        return "Pending"

    def get_next_due_date(self, obj):
        unpaid_installment = get_next_unpaid_installment_item(
            obj.staff,
            obj.course,
        )
        return get_installment_due_date_for_staff(
            obj.staff,
            unpaid_installment,
        )

    def get_overdue_days(self, obj):

        next_due = self.get_next_due_date(obj)

        if not next_due:
            return 0
        today = now().date()
        if today <= next_due:
            return 0
        return (today - next_due).days


# reports based on intern full summary
class InternSummaryReportSerializer(serializers.ModelSerializer):
    intern_id = serializers.IntegerField(source="staff.id")
    intern_name = serializers.SerializerMethodField()
    course_id = serializers.IntegerField(source="course.id")
    course_title = serializers.CharField(source="course.title")
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    overall_grade = serializers.SerializerMethodField()

    class Meta:
        model = AssignedStaffCourse
        fields = [
            "intern_id",
            "intern_name",
            "course_id",
            "course_title",
            "total_tasks",
            "completed_tasks",
            "progress",
            "payment_status",
            "overall_grade",
        ]

    def get_intern_name(self, obj):

        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"

    def get_total_tasks(self, obj):

        return TaskAssignment.objects.filter(
            staff=obj.staff,
            task__course=obj.course
        ).count()

    def get_completed_tasks(self, obj):

        return TaskAssignment.objects.filter(
            staff=obj.staff,
            task__course=obj.course,
            status="completed"
        ).count()

    def get_progress(self, obj):

        total = self.get_total_tasks(obj)

        if total == 0:
            return 0

        completed = self.get_completed_tasks(obj)

        return round((completed / total) * 100, 2)

    def get_payment_status(self, obj):

        total_fee = obj.course.total_fee

        paid = CoursePayment.objects.filter(
            student__profile=obj.staff,
            installments__plan__course=obj.course
        ).aggregate(
            total=Sum("amount_paid")
        )["total"] or 0

        if paid >= total_fee:
            return "Fully Paid"

        return "Pending"

    def get_overall_grade(self, obj):

        progress = self.get_progress(obj)

        if progress >= 90:
            return "A+"

        elif progress >= 80:
            return "A"

        elif progress >= 70:
            return "B+"

        elif progress >= 60:
            return "B"

        elif progress >= 50:
            return "C"

        else:
            return "Fail"


# report based enrollment
class EnrollmentReportSerializer(serializers.ModelSerializer):

    student_id = serializers.IntegerField(source="staff.id", read_only=True)
    student_name = serializers.SerializerMethodField()
    email = serializers.CharField(source="staff.user.email", read_only=True)
    phone = serializers.CharField(source="staff.phone_number", read_only=True)
    status = serializers.SerializerMethodField()
    course = serializers.CharField(source="course.title", read_only=True)
    enrollment_date = serializers.DateField(source="assigned_date", read_only=True)

    class Meta:

        model = AssignedStaffCourse
        fields = [
            "student_id",
            "student_name",
            "email",
            "phone",
            "status",
            "course",
            "enrollment_date",
        ]

    def get_student_name(self, obj):

        user = obj.staff.user

        return f"{user.first_name} {user.last_name}"

    def get_status(self, obj):

        job_detail = getattr(obj.staff, "job_detail", None)

        if job_detail:
            return job_detail.status
        return "Unknown"



class StudentInSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "student_id", "name", "email", "course", "batch", "is_active"]

    def get_name(self, obj):
        return obj.get_full_name()

    def get_email(self, obj):
        return obj.profile.user.email

    def _get_enrollment(self, obj):
        if not hasattr(obj, '_cached_enrollment'):
            obj._cached_enrollment = obj.enrollments.select_related(
                "course", "batch"
            ).first()
        return obj._cached_enrollment

    def get_course(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.course.title if enrollment and enrollment.course else None

    def get_batch(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.batch.batch_number if enrollment and enrollment.batch else None


class FacultyInSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    department = serializers.CharField(source="department.name", default=None)

    class Meta:
        model = Faculty
        fields = ["id", "name", "department", "is_active"]

    def get_name(self, obj):
        return obj.get_full_name()


class CourseInSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "total_fee", "is_active"]


# ── Center Serializers ────────────────────────────────────────

class CenterReportsSerializer(serializers.ModelSerializer):
    total_students = serializers.IntegerField(read_only=True)
    active_students = serializers.IntegerField(read_only=True)
    inactive_students = serializers.IntegerField(read_only=True)
    total_courses = serializers.IntegerField(read_only=True)
    faculties = serializers.IntegerField(read_only=True)

    class Meta:
        model = Center
        fields = [
            "id", "name", "country_name", "state_name", "address",
            "total_students", "active_students", "inactive_students",
            "total_courses", "faculties",
        ]


class CenterDetailReportSerializer(serializers.ModelSerializer):
    active_students = serializers.SerializerMethodField()
    inactive_students = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    faculties = serializers.SerializerMethodField()

    class Meta:
        model = Center
        fields = [
            "id", "name", "country_name", "state_name", "address",
            "active_students", "inactive_students", "courses", "faculties",
        ]

    def get_active_students(self, obj):
        qs = obj.students.filter(is_active=True).select_related("profile__user")
        return StudentInSerializer(qs, many=True).data

    def get_inactive_students(self, obj):
        qs = obj.students.filter(is_active=False).select_related("profile__user")
        return StudentInSerializer(qs, many=True).data

    def get_courses(self, obj):
        courses = Course.objects.filter(students__center=obj).distinct()
        return CourseInSerializer(courses, many=True).data

    def get_faculties(self, obj):
        faculties = Faculty.objects.filter(
            batches__students__center=obj
        ).distinct().select_related("user__user", "department")
        return FacultyInSerializer(faculties, many=True).data


# ── Batch Serializers ─────────────────────────────────────────

class BatchReportSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.title", read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Batch
        fields = [
            "id", "batch_number", "description", "course", "course_name",
            "start_date", "end_date", "is_active", "created_at", "student_count",
        ]


class BatchDetailReportSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.title", read_only=True)
    students = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = [
            "id", "batch_number", "description", "course", "course_name",
            "start_date", "end_date", "is_active", "created_at", "students",
        ]

    def get_students(self, obj):
        students = Student.objects.filter(
            enrollments__batch=obj
        ).select_related("profile__user").prefetch_related(
            "enrollments__course"
        ).distinct()
        return StudentInSerializer(students, many=True).data  


# ── Course Serializers ────────────────────────────────────────

class CourseReportSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department.name", default=None)
    total_students = serializers.IntegerField(read_only=True)
    active_students = serializers.IntegerField(read_only=True)
    inactive_students = serializers.IntegerField(read_only=True)
    total_batches = serializers.IntegerField(read_only=True)
    active_batches = serializers.IntegerField(read_only=True)
    total_faculties = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "title", "description", "department", "total_fee",
            "is_active", "created_at", "total_students", "active_students",
            "inactive_students", "total_batches", "active_batches", "total_faculties",
        ]


class CourseDetailReportSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department.name", default=None)
    batches = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    faculties = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "title", "description", "department", "total_fee",
            "is_active", "created_at", "batches", "students", "faculties",
        ]

    def get_batches(self, obj):
        return obj.batches.values(
            "id", "batch_number", "start_date", "end_date", "is_active"
        )

    def get_students(self, obj):
        students = Student.objects.filter(
            enrollments__course=obj
        ).select_related("profile__user").distinct()
        return StudentInSerializer(students, many=True).data

    def get_faculties(self, obj):
        faculties = obj.faculties.select_related("user__user", "department").all()
        return FacultyInSerializer(faculties, many=True).data


# salesperson serilizer
class SalesPersonSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    total_students = serializers.IntegerField(read_only=True)

    class Meta:
        model = SalesPerson
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "designation",
            "total_students"
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    

from django.utils.timezone import now

class FacultyReportSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    department = serializers.CharField(source="department.name", default=None)
    total_students = serializers.IntegerField(read_only=True)
    active_students = serializers.IntegerField(read_only=True)
    completed_students = serializers.IntegerField(read_only=True)
    total_batches = serializers.IntegerField(read_only=True)
    total_courses = serializers.IntegerField(read_only=True)

    class Meta:
        model = Faculty
        fields = [
            "id", "name", "department", "is_active",
            "total_courses", "total_batches",
            "total_students", "active_students", "completed_students",
        ]

    def get_name(self, obj):
        return obj.get_full_name()


class FacultyDetailReportSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    department = serializers.CharField(source="department.name", default=None)
    courses = serializers.SerializerMethodField()
    batches = serializers.SerializerMethodField()
    active_students = serializers.SerializerMethodField()
    completed_students = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = [
            "id", "name", "department", "is_active",
            "courses", "batches",
            "active_students", "completed_students",
        ]

    def get_name(self, obj):
        return obj.get_full_name()

    def get_courses(self, obj):
        return obj.courses.values("id", "title", "total_fee", "is_active")

    def get_batches(self, obj):
        return obj.batches.select_related("course").values(
            "id", "batch_number", "course__title", "start_date", "end_date", "is_active"
        )

    def get_active_students(self, obj):
        students = Student.objects.filter(
            enrollments__batch__faculties=obj,
            enrollments__batch__end_date__gte=now().date(),
            is_active=True
        ).select_related("profile__user").prefetch_related(
            "enrollments__course", "enrollments__batch"
        ).distinct()
        return StudentInSerializer(students, many=True).data

    def get_completed_students(self, obj):
        students = Student.objects.filter(
            enrollments__batch__faculties=obj,
            enrollments__batch__end_date__lt=now().date()
        ).select_related("profile__user").prefetch_related(
            "enrollments__course", "enrollments__batch"
        ).distinct()
        return StudentInSerializer(students, many=True).data




class InstallmentItemReportSerializer(serializers.ModelSerializer):
    paid_amount = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()

    class Meta:
        model = InstallmentItem
        fields = [
            "id",
            "installment_number",
            "amount",
            "due_days",
            "paid_amount",
            "balance",
            "is_paid",
        ]

    def get_paid_amount(self, obj):
        total = obj.course_payments.aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0.00")  # 0 → Decimal("0.00")
        return total

    def get_balance(self, obj):
        return obj.amount - self.get_paid_amount(obj)

    def get_is_paid(self, obj):
        return self.get_balance(obj) <= 0


from ..utils import (
    get_student_enrollments,
    get_next_unpaid_installment_item,
    get_installment_due_date_for_staff,
)

class RegistrationReportSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    place = serializers.SerializerMethodField()
    counsellor = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    center = serializers.CharField(source="center.name", default=None)
    duration = serializers.SerializerMethodField()
    course_fee = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    installments = serializers.SerializerMethodField()
    batch_end_date = serializers.SerializerMethodField()
    next_due_installment = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "student_name",
            "place",
            "counsellor",
            "course",
            "start_date",
            "center",
            "duration",
            "course_fee",
            "paid_amount",
            "balance",
            "batch_end_date",
            "next_due_installment",
            "installments",
        ]

    def _get_enrollment(self, obj):
        if not hasattr(obj, '_cached_enrollment'):
            obj._cached_enrollment = get_student_enrollments(obj).first()
        return obj._cached_enrollment

    def get_student_name(self, obj):
        return obj.get_full_name()

    def get_place(self, obj):
        return obj.center.address if obj.center else None

    def get_counsellor(self, obj):
        if obj.councellor:
            user = obj.councellor.assigned_staff.user  # .user → .assigned_staff.user
            return f"{user.first_name} {user.last_name}"
        return None

    def get_course(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.course.title if enrollment and enrollment.course else None

    def get_duration(self, obj):
        enrollment = self._get_enrollment(obj)
        if enrollment and enrollment.batch:
            delta = enrollment.batch.end_date - enrollment.batch.start_date
            return delta.days
        return None

    def get_course_fee(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.course.total_fee if enrollment and enrollment.course else None

    def get_paid_amount(self, obj):
        return obj.course_payments.aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0.00")  # 0 → Decimal("0.00")

    def get_balance(self, obj):
        course_fee = self.get_course_fee(obj)
        if course_fee is None:
            return None
        return course_fee - self.get_paid_amount(obj)

    def get_batch_end_date(self, obj):
        enrollment = self._get_enrollment(obj)
        return enrollment.batch.end_date if enrollment and enrollment.batch else None

    def get_next_due_installment(self, obj):
        enrollment = self._get_enrollment(obj)
        if not enrollment:
            return None

        next_item = get_next_unpaid_installment_item(obj, enrollment.course)
        if not next_item:
            return None

        due_date = get_installment_due_date_for_staff(obj, next_item)

        return {
            "installment_number": next_item.installment_number,
            "amount": next_item.amount,
            "due_date": due_date,
        }

    def get_installments(self, obj):
        enrollment = self._get_enrollment(obj)
        if not enrollment or not enrollment.installment_plan:
            return []
        items = enrollment.installment_plan.items.prefetch_related(
            "course_payments"
        ).all()
        return InstallmentItemReportSerializer(items, many=True).data


