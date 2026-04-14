from datetime import datetime, timedelta

def generate_batch_number(model, field_name: str, prefix: str, length: int, course):
    year = datetime.now().year

    start = 1  # 001, 002...

    # Filter course-wise + year-wise
    latest = model.objects.filter(
        course=course,
        **{f"{field_name}__startswith": f"{prefix}{year}"}
    ).order_by(f"-{field_name}").first()

    if latest:
        latest_number_str = getattr(latest, field_name)[-length:]
        next_number = int(latest_number_str) + 1
    else:
        next_number = start

    return f"{prefix}{year}{next_number:0{length}d}"


from datetime import datetime

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


def get_payment_student(actor):
    from .models import Student

    if isinstance(actor, Student):
        return actor

    return getattr(actor, "student_profile", None)


def get_staff_course_enrollment(staff, course, installment_plan=None):
    from .models import StudentCourseEnrollment

    student = get_payment_student(staff)
    if not student or not course:
        return None

    queryset = StudentCourseEnrollment.objects.select_related(
        "installment_plan"
    ).filter(
        student=student,
        course=course,
    )

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
    plan = get_staff_installment_plan(
        staff,
        course,
        preferred_plan=preferred_plan,
    )
    if not plan or not student:
        return None

    return plan.items.exclude(
        payments__student=student
    ).order_by(
        "installment_number",
        "due_days",
        "id",
    ).first()


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
