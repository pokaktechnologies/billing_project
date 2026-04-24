from datetime import datetime, timedelta

from django.db.models import Count, OuterRef, Prefetch, Q, Subquery, Sum


def generate_batch_number(model, field_name: str, prefix: str, length: int, course):
    year = datetime.now().year
    start = 1

    latest = model.objects.select_for_update().filter(
        course=course,
        **{f"{field_name}__startswith": f"{prefix}{year}"}
    ).order_by(f"-{field_name}").first()

    if latest:
        latest_number_str = getattr(latest, field_name)[-length:]
        next_number = int(latest_number_str) + 1
    else:
        next_number = start

    return f"{prefix}{year}{next_number:0{length}d}"

def generate_student_id(model, field_name: str, prefix: str, length: int):
    year = datetime.now().year

    latest = model.objects.select_for_update().filter(
        **{f"{field_name}__startswith": f"{prefix}{year}"}
    ).order_by(f"-{field_name}").first()

    if latest:
        latest_number_str = getattr(latest, field_name)[-length:]
        next_number = int(latest_number_str) + 1
    else:
        next_number = 1

    return f"{prefix}{year}{next_number:0{length}d}"

def get_clean_prefix(title):
    import re
    clean = re.sub(r'[^A-Za-z0-9 ]', '', title)
    words = clean.split()

    if len(words) > 1:
        return ''.join([w[0] for w in words]).upper()
    return clean[:3].upper()


def get_authenticated_student(user):
    if not user:
        return None

    staff_profile = getattr(user, "staff_profile", None)
    if not staff_profile:
        return None

    return getattr(staff_profile, "student_profile", None)


def get_payment_student(actor):
    from .models import Student

    if not actor:
        return None

    if isinstance(actor, Student):
        return actor

    student = get_authenticated_student(actor)
    if student:
        return student

    return getattr(actor, "student_profile", None)


def get_student_enrollments(student):
    from .models import StudentCourseEnrollment

    if not student:
        return StudentCourseEnrollment.objects.none()

    return (
        StudentCourseEnrollment.objects
        .filter(student=student)
        .select_related("course", "batch", "installment_plan")
    )


def get_student_course_ids(student):
    return get_student_enrollments(student).values_list("course_id", flat=True)


def get_student_courses_queryset(student):
    from .models import Course

    if not student:
        return Course.objects.none()

    return (
        Course.objects
        .filter(enrollments__student=student)
        .select_related("department", "tax_settings")
        .prefetch_related("installment_plans__items", "batches__faculties__user__user")
        .annotate(
            students_count=Count("students", distinct=True),
            study_material_count=Count(
                "studymaterial",
                filter=Q(studymaterial__is_public=True),
                distinct=True,
            ),
        )
        .distinct()
        .order_by("-created_at")
    )


def get_student_task_assignments(student):
    from .models import TaskAssignment

    if not student:
        return TaskAssignment.objects.none()

    return (
        TaskAssignment.objects
        .filter(student=student)
        .order_by("-assigned_at")
        .select_related(
            "task",
            "task__course",
            "student",
            "student__profile__user",
            "staff",
            "staff__user",
        )
    )


def get_student_task_assignment(task, student):
    if not student or not task:
        return None

    prefetched_assignments = getattr(task, "student_assignments", None)
    if prefetched_assignments is not None:
        return prefetched_assignments[0] if prefetched_assignments else None

    return (
        get_student_task_assignments(student)
        .filter(task=task)
        .first()
    )


def get_student_tasks_queryset(student):
    from .models import Task, TaskAssignment

    if not student:
        return Task.objects.none()

    latest_assignment_subquery = (
        TaskAssignment.objects
        .filter(task=OuterRef("pk"), student=student)
        .order_by("-assigned_at")
    )

    return (
        Task.objects
        .filter(assignments__student=student)
        .select_related("course")
        .prefetch_related(
            "attachments",
            Prefetch(
                "assignments",
                queryset=get_student_task_assignments(student),
                to_attr="student_assignments",
            ),
        )
        .distinct()
        .annotate(
            latest_status=Subquery(
                latest_assignment_subquery.values("status")[:1]
            )
        )
    )


def get_student_submissions_queryset(student):
    from .models import TaskSubmission

    if not student:
        return TaskSubmission.objects.none()

    return (
        TaskSubmission.objects
        .filter(assignment__student=student)
        .select_related(
            "assignment",
            "assignment__task",
            "assignment__task__course",
            "assignment__student",
            "assignment__student__profile__user",
            "assignment__staff",
            "assignment__staff__user",
        )
        .prefetch_related("attachments", "assignment__task__attachments")
        .order_by("-submitted_at", "-id")
    )


def get_staff_course_enrollment(staff, course, installment_plan=None):
    student = get_payment_student(staff)
    if not student or not course:
        return None

    queryset = get_student_enrollments(student).filter(course=course)

    if installment_plan:
        matched = queryset.filter(installment_plan=installment_plan).first()
        if matched:
            return matched

    return queryset.first()


def get_staff_installment_plan(staff, course, preferred_plan=None):
    from .models import InstallmentPlan

    if preferred_plan and preferred_plan.course_id == getattr(course, "id", None):
        return preferred_plan

    enrollment = get_staff_course_enrollment(
        staff,
        course,
        installment_plan=preferred_plan,
    )
    if enrollment and enrollment.installment_plan_id:
        return enrollment.installment_plan

    student = get_payment_student(staff)
    if (
        student and
        student.course_id == getattr(course, "id", None) and
        student.payment_type_id
    ):
        return student.payment_type

    if preferred_plan and preferred_plan.course_id == getattr(course, "id", None):
        return preferred_plan

    active_plans = list(
        InstallmentPlan.objects.filter(
            course=course,
            is_active=True,
        ).order_by("total_installments", "id")[:2]
    )
    if len(active_plans) == 1:
        return active_plans[0]

    return None


def get_staff_course_start_date(staff, course, installment_plan=None):
    from .models import AssignedStaffCourse

    enrollment = get_staff_course_enrollment(
        staff,
        course,
        installment_plan=installment_plan,
    )
    if enrollment:
        return enrollment.enrollment_date

    student = get_payment_student(staff)
    profile = getattr(student, "profile", None) if student else None

    assignment = AssignedStaffCourse.objects.filter(
        staff=profile or staff,
        course=course,
    ).only("assigned_date").first()
    if assignment:
        return assignment.assigned_date

    if student and student.course_id == getattr(course, "id", None):
        return student.start_date

    return None


def get_next_unpaid_installment_item(staff, course, preferred_plan=None):
    student = get_payment_student(staff)
    plan = get_staff_installment_plan(staff, course, preferred_plan=preferred_plan)
    if not plan or not student:
        return None

    # "course_payments" related_name use ചെയ്യുക
    # Fully paid items exclude ചെയ്യുക (partial ആയവ still show ചെയ്യണം)
    fully_paid_item_ids = []
    for item in plan.items.all():
        paid = item.course_payments.filter(
            student=student
        ).aggregate(t=Sum("amount_paid"))["t"] or 0
        if paid >= item.amount:
            fully_paid_item_ids.append(item.id)

    return plan.items.exclude(
        id__in=fully_paid_item_ids
    ).order_by("installment_number", "due_days", "id").first()


def get_installment_due_date_for_staff(staff, installment):
    if not installment:
        return None

    course = getattr(getattr(installment, "plan", None), "course", None)
    if not course:
        return None

    start_date = get_staff_course_start_date(
        staff,
        course,
        installment_plan=installment.plan,
    )
    if not start_date:
        return None

    return start_date + timedelta(days=installment.due_days)
