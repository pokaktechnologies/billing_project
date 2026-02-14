from datetime import timedelta

from django.db.models import Sum
from django.utils.timezone import now
from rest_framework import serializers

from accounts.models import StaffProfile
from internship.models import TaskSubmission, AssignedStaffCourse, CoursePayment, CourseInstallment, TaskAssignment


# report based on task
class TaskReportSerializer(serializers.ModelSerializer):
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
            "course_id",
            "course_title",
            "total_fee",
            "paid_amount",
            "pending_amount",
            "payment_status",
            "next_due_date",
            "overdue_days",
        ]

    def get_paid_amount(self, obj):

        total = CoursePayment.objects.filter(
            staff=obj.staff,
            installment__course=obj.course
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

        unpaid_installment = CourseInstallment.objects.filter(
            course=obj.course
        ).exclude(
            payments__staff=obj.staff
        ).order_by(
            "due_days_after_enrollment"
        ).first()

        if not unpaid_installment:
            return None

        return obj.assigned_date + \
               timedelta(days=unpaid_installment.due_days_after_enrollment)

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
            staff=obj.staff,
            installment__course=obj.course
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
