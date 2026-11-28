from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Count, Q, Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from accounts.permissions import HasModulePermission
from internship.models import (
    InternshipApplication,
    Student,
    StudentCourseEnrollment,
    Course,
    Batch,
    Faculty,
    Class,
    Section,
    SectionDay,
    Center,
    StudentInstallmentItem,
    CoursePayment,
    TaskAssignment,
    TaskSubmission,
    LiveClass,
    RecordedClass,
    ClassAttendanceSession,
    StudentReport,
    ReportTemplate,
    Test,
    TestAttempt,
    TestAnswer,
)
from internship.serializers.pending_dashboard import AcademicPendingDashboardSerializer


class AcademicPendingDashboardAPIView(APIView):
    """
    Academic Module Pending Works Dashboard API.
    
    Returns all actionable pending tasks across Academic submodules:
      - registration_form: Unconverted applications, unconfirmed slots, missing documents
      - admissions: Students without enrollments, unassigned batches, unassigned learning modes
      - courses: Missing faculties, missing installment plans, missing active batches
      - students: Inactive student accounts, missing counsellors, overdue assigned tasks
      - faculty: Unassigned faculty, pending task submission reviews, draft reports, test grading
      - payments: Enrollments with pending balance, overdue installments
      - classes: Classrooms without sections, sections without days, overdue live classes
      - center: Centers without classrooms, centers without students
    
    Query Parameters:
      - tab: Filter by specific tab (e.g. 'registration_form', 'admissions', 'courses', 'students', 'faculty', 'payments', 'classes', 'center'). Default: 'all'.
      - urgency: Filter by urgency level ('high', 'medium', 'low').
      - search: Search text across item titles, descriptions, and student/applicant names.
      - limit: Maximum items to return in the items array (default: 100).
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "registration_form", "label": "Registration Form"},
        {"key": "admissions", "label": "Admissions"},
        {"key": "courses", "label": "Courses"},
        {"key": "students", "label": "Students"},
        {"key": "faculty", "label": "Faculty"},
        {"key": "payments", "label": "Payments"},
        {"key": "classes", "label": "Classes"},
        {"key": "center", "label": "Center"},
    ]

    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()

        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(tab_key, work_type, work_type_label, title, description, urgency, record_id=None, item_id=None, created_at=None, due_date=None, action_url=None, meta=None):
            if not item_id:
                item_id = f"{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"
            
            # Category counter
            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {"key": work_type, "label": work_type_label, "count": 0}
            tab_categories[tab_key][work_type]["count"] += 1

            tab_label = next((t["label"] for t in self.TAB_DEFINITIONS if t["key"] == tab_key), tab_key.replace("_", " ").title())

            item = {
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": tab_label,
                "work_type": work_type,
                "work_type_label": work_type_label,
                "title": title,
                "description": description,
                "urgency": urgency,
                "created_at": created_at,
                "due_date": due_date,
                "action_url": action_url,
                "meta": meta or {},
            }
            tab_items[tab_key].append(item)

        # =========================================================================
        # 1. TAB: REGISTRATION FORM (InternshipApplication)
        # =========================================================================
        unconverted_apps = InternshipApplication.objects.filter(
            is_converted=False
        ).select_related("course", "councellor").prefetch_related("documents")

        for app in unconverted_apps:
            applicant_name = f"{app.first_name} {app.last_name}".strip()
            course_title = app.course.title if app.course else "No Course"
            counsellor_name = f"{app.councellor.first_name} {app.councellor.last_name or ''}".strip() if app.councellor else "Unassigned"
            has_docs = app.documents.exists()
            days_since = (today - app.created_at.date()).days if app.created_at else 0
            urgency = "high" if days_since > 3 else "medium"

            # 1a. Unconverted Application
            add_item(
                tab_key="registration_form",
                work_type="unconverted_application",
                work_type_label="Unconverted Application",
                title=f"{applicant_name} - Pending Student Conversion",
                description=f"Registration submitted on {app.created_at.strftime('%d-%b-%Y') if app.created_at else 'N/A'} for course '{course_title}'. Conversion to student is pending.",
                urgency=urgency,
                record_id=app.id,
                item_id=f"reg_app_unconv_{app.id}",
                created_at=app.created_at,
                action_url=f"/internship/applications/{app.id}/convert/",
                meta={
                    "applicant_name": applicant_name,
                    "email": app.email,
                    "phone": app.primary_phone,
                    "course_id": app.course_id,
                    "course_title": course_title,
                    "counsellor_name": counsellor_name,
                    "slot_amount": str(app.slot_amount or "0.00"),
                    "slot_paid": bool(app.slot_payment_date),
                    "days_pending": days_since,
                }
            )

            # 1b. Unconfirmed Slot Payment
            if app.slot_amount and app.slot_amount > 0 and not app.slot_payment_date:
                add_item(
                    tab_key="registration_form",
                    work_type="unconfirmed_slot_payment",
                    work_type_label="Unconfirmed Slot Payment",
                    title=f"{applicant_name} - Slot Payment Unconfirmed (₹{app.slot_amount})",
                    description=f"Slot amount of ₹{app.slot_amount} was specified, but payment date/confirmation is pending.",
                    urgency="medium",
                    record_id=app.id,
                    item_id=f"reg_app_slot_{app.id}",
                    created_at=app.created_at,
                    action_url=f"/internship/applications/{app.id}/slot-confirmation/",
                    meta={
                        "applicant_name": applicant_name,
                        "slot_amount": str(app.slot_amount),
                        "email": app.email,
                        "phone": app.primary_phone,
                    }
                )

            # 1c. Missing Verification Documents
            if not has_docs:
                add_item(
                    tab_key="registration_form",
                    work_type="missing_documents",
                    work_type_label="Missing Documents",
                    title=f"{applicant_name} - Missing Verification Documents",
                    description=f"Applicant has not uploaded qualification or legal documents.",
                    urgency="low",
                    record_id=app.id,
                    item_id=f"reg_app_docs_{app.id}",
                    created_at=app.created_at,
                    action_url=f"/internship/applications/{app.id}/",
                    meta={"applicant_name": applicant_name, "email": app.email}
                )

        # =========================================================================
        # 2. TAB: ADMISSIONS (Student, StudentCourseEnrollment)
        # =========================================================================
        # 2a. Students without any course enrollment
        admitted_no_enr = Student.objects.filter(
            enrollments__isnull=True
        ).select_related("profile__user", "center")

        for student in admitted_no_enr:
            student_name = student.get_full_name()
            add_item(
                tab_key="admissions",
                work_type="admitted_without_enrollment",
                work_type_label="Admitted Without Course",
                title=f"{student_name} ({student.student_id}) - No Course Enrolled",
                description=f"Student was admitted, but has no course enrollment record configured.",
                urgency="high",
                record_id=student.id,
                item_id=f"adm_no_enr_{student.id}",
                created_at=student.created_at,
                due_date=student.start_date,
                action_url=f"/internship/enrollments/",
                meta={
                    "student_id": student.student_id,
                    "student_name": student_name,
                    "center": student.center.name if student.center else "No Center",
                    "start_date": str(student.start_date) if student.start_date else None,
                }
            )

        # 2b. Enrollments without batch assigned
        unassigned_batch_enrs = StudentCourseEnrollment.objects.filter(
            batch__isnull=True
        ).select_related("student__profile__user", "course")

        for enr in unassigned_batch_enrs:
            student_name = enr.student.get_full_name()
            course_title = enr.course.title if enr.course else "No Course"
            add_item(
                tab_key="admissions",
                work_type="unassigned_batch",
                work_type_label="Batch Assignment Pending",
                title=f"{student_name} - Batch Assignment Pending ({course_title})",
                description=f"Student is enrolled in '{course_title}', but has not been assigned to any running batch.",
                urgency="high",
                record_id=enr.id,
                item_id=f"adm_no_batch_{enr.id}",
                created_at=timezone.make_aware(timezone.datetime.combine(enr.enrollment_date, timezone.datetime.min.time())) if enr.enrollment_date else None,
                action_url=f"/internship/enrollments/{enr.id}/",
                meta={
                    "enrollment_id": enr.id,
                    "student_id": enr.student.student_id,
                    "student_name": student_name,
                    "course_id": enr.course_id,
                    "course_title": course_title,
                }
            )

        # 2c. Enrollments with unassigned learning_type
        unassigned_lt_enrs = StudentCourseEnrollment.objects.filter(
            learning_type__isnull=True
        ).select_related("student__profile__user", "course")

        for enr in unassigned_lt_enrs:
            student_name = enr.student.get_full_name()
            course_title = enr.course.title if enr.course else "No Course"
            add_item(
                tab_key="admissions",
                work_type="unassigned_learning_type",
                work_type_label="Delivery Mode Unassigned",
                title=f"{student_name} - Learning Mode Unassigned ({course_title})",
                description=f"Delivery mode (Online / Offline / Recorded) is not specified for this course enrollment.",
                urgency="medium",
                record_id=enr.id,
                item_id=f"adm_no_lt_{enr.id}",
                action_url=f"/internship/enrollments/{enr.id}/",
                meta={
                    "enrollment_id": enr.id,
                    "student_id": enr.student.student_id,
                    "student_name": student_name,
                    "course_title": course_title,
                }
            )

        # =========================================================================
        # 3. TAB: COURSES (Course, Batch)
        # =========================================================================
        active_courses = Course.objects.filter(is_active=True).prefetch_related("faculties", "installment_plans", "batches")

        for course in active_courses:
            # 3a. Course without faculty
            if not course.faculties.exists():
                add_item(
                    tab_key="courses",
                    work_type="course_missing_faculty",
                    work_type_label="No Faculty Assigned",
                    title=f"Course '{course.title}' - No Faculty Assigned",
                    description=f"Active course '{course.title}' has no instructors assigned to teach it.",
                    urgency="high",
                    record_id=course.id,
                    item_id=f"course_no_fac_{course.id}",
                    action_url=f"/internship/course/{course.id}/",
                    meta={"course_id": course.id, "course_title": course.title, "total_fee": str(course.total_fee)}
                )

            # 3b. Course without installment plan
            if not course.installment_plans.exists():
                add_item(
                    tab_key="courses",
                    work_type="course_missing_installment_plan",
                    work_type_label="No Installment Plan",
                    title=f"Course '{course.title}' - No Installment Plan",
                    description=f"Course has no installment plans configured for flexible student payments.",
                    urgency="medium",
                    record_id=course.id,
                    item_id=f"course_no_plan_{course.id}",
                    action_url=f"/internship/installment-plan/",
                    meta={"course_id": course.id, "course_title": course.title}
                )

            # 3c. Course without active batches
            has_active_batches = any(b.is_active for b in course.batches.all())
            if not has_active_batches:
                add_item(
                    tab_key="courses",
                    work_type="course_no_active_batch",
                    work_type_label="No Active Batches",
                    title=f"Course '{course.title}' - No Active Batches",
                    description=f"Course currently has no active running batches for student enrollment.",
                    urgency="medium",
                    record_id=course.id,
                    item_id=f"course_no_batch_{course.id}",
                    action_url=f"/internship/batch/",
                    meta={"course_id": course.id, "course_title": course.title}
                )

        # =========================================================================
        # 4. TAB: STUDENTS (Student, TaskAssignment)
        # =========================================================================
        # 4a. Inactive students
        inactive_students = Student.objects.filter(
            Q(is_active=False) | Q(status="inactive")
        ).select_related("profile__user")

        for st in inactive_students:
            st_name = st.get_full_name()
            add_item(
                tab_key="students",
                work_type="inactive_student",
                work_type_label="Inactive Account",
                title=f"{st_name} ({st.student_id}) - Inactive Student Account",
                description=f"Student account is currently inactive or suspended.",
                urgency="low",
                record_id=st.id,
                item_id=f"st_inactive_{st.id}",
                action_url=f"/internship/students/{st.id}/",
                meta={"student_id": st.student_id, "student_name": st_name}
            )

        # 4b. Students missing counsellor
        no_counsellor_students = Student.objects.filter(
            councellor__isnull=True, is_active=True
        ).select_related("profile__user")

        for st in no_counsellor_students:
            st_name = st.get_full_name()
            add_item(
                tab_key="students",
                work_type="missing_counsellor",
                work_type_label="No Counsellor Assigned",
                title=f"{st_name} ({st.student_id}) - No Counsellor Assigned",
                description=f"Student has no academic counsellor assigned for progress monitoring.",
                urgency="low",
                record_id=st.id,
                item_id=f"st_no_counc_{st.id}",
                action_url=f"/internship/students/{st.id}/",
                meta={"student_id": st.student_id, "student_name": st_name}
            )

        # 4c. Overdue student tasks
        overdue_tasks = TaskAssignment.objects.filter(
            status="pending",
            task__due_date__lt=today
        ).select_related("student__profile__user", "task__course")

        for ta in overdue_tasks:
            st_name = ta.student.get_full_name() if ta.student else "Student"
            task_title = ta.task.title if ta.task else "Task"
            due_date = ta.task.due_date if ta.task else None
            add_item(
                tab_key="students",
                work_type="student_task_overdue",
                work_type_label="Overdue Task Submission",
                title=f"{st_name} - Task '{task_title}' Overdue",
                description=f"Task was due on {due_date} but remains pending submission.",
                urgency="medium",
                record_id=ta.id,
                item_id=f"st_task_overdue_{ta.id}",
                due_date=due_date,
                action_url=f"/internship/instructor/tasks/{ta.task_id}/",
                meta={"student_name": st_name, "task_title": task_title, "due_date": str(due_date)}
            )

        # =========================================================================
        # 5. TAB: FACULTY (Faculty, TaskAssignment, StudentReport, TestAnswer)
        # =========================================================================
        # 5a. Active faculty without courses
        unassigned_fac = Faculty.objects.filter(
            is_active=True, courses__isnull=True
        ).select_related("user__user")

        for fac in unassigned_fac:
            fac_name = fac.get_full_name()
            add_item(
                tab_key="faculty",
                work_type="unassigned_faculty",
                work_type_label="No Courses Assigned",
                title=f"Faculty '{fac_name}' - No Courses Assigned",
                description=f"Active faculty member is not assigned to teach any courses.",
                urgency="medium",
                record_id=fac.id,
                item_id=f"fac_no_course_{fac.id}",
                action_url=f"/internship/faculty/{fac.id}/",
                meta={"faculty_id": fac.id, "faculty_name": fac_name}
            )

        # 5b. Task submissions awaiting faculty review
        pending_reviews = TaskAssignment.objects.filter(
            status="submitted"
        ).select_related("student__profile__user", "task__course")

        for ta in pending_reviews:
            st_name = ta.student.get_full_name() if ta.student else "Student"
            task_title = ta.task.title if ta.task else "Task"
            add_item(
                tab_key="faculty",
                work_type="pending_task_review",
                work_type_label="Task Review Pending",
                title=f"Submission by {st_name} - '{task_title}'",
                description=f"Student submitted task '{task_title}'. Awaiting instructor grading & feedback.",
                urgency="high",
                record_id=ta.id,
                item_id=f"fac_sub_rev_{ta.id}",
                action_url=f"/internship/instructor/submissions/",
                meta={"student_name": st_name, "task_title": task_title, "task_id": ta.task_id}
            )

        # 5c. Draft student reports
        draft_reports = StudentReport.objects.filter(
            status="draft"
        ).select_related("student__profile__user", "batch", "course")

        for rep in draft_reports:
            st_name = rep.student.get_full_name()
            course_title = rep.course.title if rep.course else "Course"
            add_item(
                tab_key="faculty",
                work_type="draft_student_report",
                work_type_label="Draft Report",
                title=f"Draft Report - {st_name} ({course_title})",
                description=f"Student performance report is in draft status and has not been submitted.",
                urgency="medium",
                record_id=rep.id,
                item_id=f"fac_rep_draft_{rep.id}",
                created_at=rep.created_at,
                action_url=f"/internship/instructor/reports/{rep.id}/",
                meta={"student_name": st_name, "course_title": course_title, "batch_number": rep.batch.batch_number if rep.batch else None}
            )

        # 5d. Descriptive test answers awaiting evaluation
        pending_tests = TestAnswer.objects.filter(
            question__manual_evaluation=True,
            marks_awarded__isnull=True,
            attempt__status="submitted"
        ).select_related("attempt__student__profile__user", "attempt__test")[:50]

        for ans in pending_tests:
            st_name = ans.attempt.student.get_full_name()
            test_name = ans.attempt.test.name if ans.attempt.test else "Test"
            add_item(
                tab_key="faculty",
                work_type="pending_test_evaluation",
                work_type_label="Test Grading Pending",
                title=f"Test Grading - {st_name} ({test_name})",
                description=f"Descriptive answer in test '{test_name}' is awaiting manual score evaluation.",
                urgency="high",
                record_id=ans.id,
                item_id=f"fac_test_eval_{ans.id}",
                action_url=f"/internship/instructor/tests/{ans.attempt.test_id}/submissions/",
                meta={"student_name": st_name, "test_name": test_name}
            )

        # =========================================================================
        # 6. TAB: PAYMENTS (StudentCourseEnrollment, CoursePayment)
        # =========================================================================
        enrollments = StudentCourseEnrollment.objects.select_related(
            "student__profile__user", "course"
        ).prefetch_related("payments")

        for enr in enrollments:
            total_paid = sum((p.amount_paid for p in enr.payments.all()), Decimal("0.00"))
            balance = enr.effective_discounted_fee - total_paid

            if balance > Decimal("0.00"):
                st_name = enr.student.get_full_name()
                course_title = enr.course.title if enr.course else "Course"
                urgency = "high" if balance > Decimal("20000.00") else "medium"
                add_item(
                    tab_key="payments",
                    work_type="pending_course_balance",
                    work_type_label="Pending Course Fee Balance",
                    title=f"{st_name} - Pending Balance ₹{balance:,.2f} ({course_title})",
                    description=f"Outstanding fee balance for course '{course_title}'. Paid: ₹{total_paid:,.2f} / ₹{enr.effective_discounted_fee:,.2f}.",
                    urgency=urgency,
                    record_id=enr.id,
                    item_id=f"pay_bal_{enr.id}",
                    action_url=f"/internship/payments-list/",
                    meta={
                        "enrollment_id": enr.id,
                        "student_id": enr.student.student_id,
                        "student_name": st_name,
                        "course_title": course_title,
                        "effective_fee": str(enr.effective_discounted_fee),
                        "total_paid": str(total_paid),
                        "pending_balance": str(balance),
                    }
                )

        # =========================================================================
        # 7. TAB: CLASSES (Class, Section, LiveClass)
        # =========================================================================
        # 7a. Classes without sections
        empty_classes = Class.objects.filter(
            is_active=True, sections__isnull=True
        ).select_related("center")

        for cls in empty_classes:
            add_item(
                tab_key="classes",
                work_type="class_without_sections",
                work_type_label="No Sections Configured",
                title=f"Classroom '{cls.name}' - No Sections Configured",
                description=f"Classroom at center '{cls.center.name}' has no active sections or schedules.",
                urgency="low",
                record_id=cls.id,
                item_id=f"cls_no_sec_{cls.id}",
                action_url=f"/internship/class/{cls.id}/",
                meta={"class_id": cls.id, "class_name": cls.name, "center_name": cls.center.name}
            )

        # 7b. Sections without scheduled days
        empty_sections = Section.objects.filter(
            days__isnull=True
        ).select_related("class_obj", "batch")

        for sec in empty_sections:
            add_item(
                tab_key="classes",
                work_type="section_missing_days",
                work_type_label="Missing Day Schedule",
                title=f"Section '{sec.class_obj.name} - {sec.batch.batch_number}' - Missing Day Schedule",
                description=f"Section has defined hours ({sec.start_time} - {sec.end_time}) but no days of week configured.",
                urgency="medium",
                record_id=sec.id,
                item_id=f"sec_no_days_{sec.id}",
                action_url=f"/internship/sections/{sec.id}/",
                meta={"section_id": sec.id}
            )

        # 7c. Overdue scheduled live classes
        overdue_live_classes = LiveClass.objects.filter(
            status="scheduled",
            scheduled_start_time__lte=now
        ).select_related("course", "batch")

        for lc in overdue_live_classes:
            add_item(
                tab_key="classes",
                work_type="overdue_live_class",
                work_type_label="Overdue Live Class",
                title=f"Live Class '{lc.title}' - Scheduled Start Time Passed",
                description=f"Live class was scheduled for {lc.scheduled_start_time.strftime('%d-%b-%Y %I:%M %p')}, but has not been started.",
                urgency="high",
                record_id=lc.id,
                item_id=f"lc_overdue_{lc.id}",
                action_url=f"/internship/live-classes/{lc.id}/",
                meta={"live_class_id": lc.id, "course_title": lc.course.title if lc.course else None}
            )

        # =========================================================================
        # 8. TAB: CENTER (Center)
        # =========================================================================
        # 8a. Centers without classes
        centers_no_classes = Center.objects.filter(classes__isnull=True)
        for c in centers_no_classes:
            add_item(
                tab_key="center",
                work_type="center_without_classes",
                work_type_label="No Classrooms Configured",
                title=f"Center '{c.name}' - No Classrooms Configured",
                description=f"Training center has no physical or virtual classrooms set up.",
                urgency="low",
                record_id=c.id,
                item_id=f"center_no_cls_{c.id}",
                action_url=f"/internship/centers/{c.id}/",
                meta={"center_id": c.id, "center_name": c.name}
            )

        # 8b. Centers without students
        centers_no_students = Center.objects.filter(students__isnull=True)
        for c in centers_no_students:
            add_item(
                tab_key="center",
                work_type="center_without_students",
                work_type_label="No Enrolled Students",
                title=f"Center '{c.name}' - No Enrolled Students",
                description=f"Center has zero registered or admitted students.",
                urgency="low",
                record_id=c.id,
                item_id=f"center_no_st_{c.id}",
                action_url=f"/internship/centers/{c.id}/",
                meta={"center_id": c.id, "center_name": c.name}
            )

        # =========================================================================
        # BUILD TAB METADATA & FILTERING
        # =========================================================================
        tab_counts = {tab["key"]: len(tab_items[tab["key"]]) for tab in self.TAB_DEFINITIONS}
        total_pending_count = sum(tab_counts.values())

        tabs_data = []
        for tab_def in self.TAB_DEFINITIONS:
            k = tab_def["key"]
            cat_list = list(tab_categories[k].values())
            tabs_data.append({
                "key": k,
                "label": tab_def["label"],
                "count": tab_counts[k],
                "categories": cat_list,
            })

        # Gather target items based on active_tab
        if active_tab in tab_items:
            combined_items = tab_items[active_tab]
        else:
            active_tab = "all"
            combined_items = []
            for k in [t["key"] for t in self.TAB_DEFINITIONS]:
                combined_items.extend(tab_items[k])

        # Filter by urgency
        if urgency_filter in ["high", "medium", "low"]:
            combined_items = [it for it in combined_items if it["urgency"] == urgency_filter]

        # Filter by search query
        if search_query:
            combined_items = [
                it for it in combined_items
                if search_query in it["title"].lower()
                or search_query in it["description"].lower()
                or search_query in str(it.get("meta", {})).lower()
            ]

        # Sort: high urgency first, then medium, then low
        urgency_priority = {"high": 1, "medium": 2, "low": 3}
        combined_items.sort(key=lambda x: urgency_priority.get(x["urgency"], 4))

        # Limit items
        if limit_param.isdigit():
            limit_val = int(limit_param)
            if limit_val > 0:
                combined_items = combined_items[:limit_val]

        response_data = {
            "module": "academic",
            "module_label": "Academy",
            "total_pending_count": total_pending_count,
            "tab_counts": tab_counts,
            "tabs": tabs_data,
            "active_tab": active_tab,
            "items_count": len(combined_items),
            "items": combined_items,
        }

        serializer = AcademicPendingDashboardSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FacultyPendingDashboardAPIView(APIView):
    """
    Faculty Management Pending Controls Dashboard API.

    Returns all actionable pending items for the logged-in faculty member
    (or all faculties if superuser/admin, optionally filtered by ?faculty_id=<id>):
      - submissions: Pending task submission reviews & ungraded descriptive test answers
      - faculty_attendance: Today's & recent (7 days) unmarked section attendance
      - schedule: Overdue scheduled live classes & unended live classes
      - faculty_reports: Draft student reports & completed students missing reports
      - my_courses: Draft tests & unpublished recorded classes
      - faculty_interns: Overdue student task assignments

    Query Parameters:
      - tab: 'all' (default), 'submissions', 'faculty_attendance', 'schedule',
             'faculty_reports', 'my_courses', 'faculty_interns'
      - urgency: 'high', 'medium', 'low'
      - search: Case-insensitive search across title, description, and meta
      - limit: Maximum items to return (default: 100)
      - faculty_id: Optional (admin/superuser only) to scope to a specific Faculty
    """
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "faculty_pending"

    TAB_DEFINITIONS = [
        {"key": "submissions", "label": "Submissions"},
        {"key": "faculty_attendance", "label": "Attendance"},
        {"key": "schedule", "label": "Schedule"},
        {"key": "faculty_reports", "label": "Reports"},
        {"key": "my_courses", "label": "My Courses"},
        {"key": "faculty_interns", "label": "Interns"},
    ]

    DAY_CODE_MAP = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}

    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()

        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()
        faculty_id_param = request.query_params.get("faculty_id", "").strip()

        # Determine faculty scope
        if request.user.is_superuser:
            if faculty_id_param.isdigit():
                faculty_qs = Faculty.objects.filter(id=int(faculty_id_param))
            else:
                faculty_qs = Faculty.objects.all()
        else:
            faculty_qs = Faculty.objects.filter(user__user=request.user)

        faculty_ids = list(faculty_qs.values_list("id", flat=True))
        batch_ids = list(
            Batch.objects.filter(faculties__id__in=faculty_ids).values_list("id", flat=True).distinct()
        )
        course_ids = list(
            Course.objects.filter(
                Q(batches__id__in=batch_ids) | Q(faculties__id__in=faculty_ids)
            ).values_list("id", flat=True).distinct()
        )

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(tab_key, work_type, work_type_label, title, description, urgency, record_id=None, item_id=None, created_at=None, due_date=None, action_url=None, meta=None):
            if not item_id:
                item_id = f"{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"

            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {"key": work_type, "label": work_type_label, "count": 0}
            tab_categories[tab_key][work_type]["count"] += 1

            tab_label = next((t["label"] for t in self.TAB_DEFINITIONS if t["key"] == tab_key), tab_key.replace("_", " ").title())

            tab_items[tab_key].append({
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": tab_label,
                "work_type": work_type,
                "work_type_label": work_type_label,
                "title": title,
                "description": description,
                "urgency": urgency,
                "created_at": created_at,
                "due_date": due_date,
                "action_url": action_url,
                "meta": meta or {},
            })

        if faculty_ids:
            # =====================================================================
            # 1. TAB: SUBMISSIONS (Task Submissions & Test Evaluations)
            # =====================================================================
            pending_submissions = TaskAssignment.objects.filter(
                status="submitted"
            ).filter(
                Q(task__batch_id__in=batch_ids) | Q(task__course_id__in=course_ids)
            ).select_related("task", "task__course", "task__batch", "student", "student__profile", "student__profile__user").distinct()

            for assign in pending_submissions:
                student_name = assign.student.profile.user.get_full_name() if assign.student and assign.student.profile and assign.student.profile.user else "Student"
                days_since = (today - assign.assigned_at.date()).days if assign.assigned_at else 0
                urgency = "high" if days_since > 2 else "medium"
                add_item(
                    tab_key="submissions",
                    work_type="task_submission_pending_review",
                    work_type_label="Task Submission Pending Review",
                    title=f"{student_name} - '{assign.task.title}' Review Pending",
                    description=f"Task submission for '{assign.task.title}' is awaiting faculty review.",
                    urgency=urgency,
                    record_id=assign.id,
                    item_id=f"fac_sub_review_{assign.id}",
                    created_at=assign.assigned_at,
                    due_date=assign.task.due_date,
                    action_url=f"/internship/instructor/submissions/{assign.id}/review/",
                    meta={
                        "assignment_id": assign.id,
                        "task_id": assign.task_id,
                        "task_title": assign.task.title,
                        "student_id": assign.student_id,
                        "student_name": student_name,
                        "course_title": assign.task.course.title if assign.task.course else None,
                        "batch_number": assign.task.batch.batch_number if assign.task.batch else None,
                    }
                )

            ungraded_answers = TestAnswer.objects.filter(
                attempt__status="submitted",
                attempt__test__batch_id__in=batch_ids,
                question__section__section_type="descriptive",
                reviewed_at__isnull=True,
                marks_awarded__isnull=True,
            ).select_related(
                "attempt", "attempt__test", "attempt__student", "attempt__student__profile", "attempt__student__profile__user"
            )

            seen_attempts = set()
            for ans in ungraded_answers:
                if ans.attempt_id in seen_attempts:
                    continue
                seen_attempts.add(ans.attempt_id)
                attempt = ans.attempt
                student_name = attempt.student.profile.user.get_full_name() if attempt.student and attempt.student.profile and attempt.student.profile.user else "Student"
                submitted_date = attempt.submitted_at.date() if attempt.submitted_at else today
                days_since = (today - submitted_date).days
                urgency = "high" if days_since > 2 else "medium"
                add_item(
                    tab_key="submissions",
                    work_type="test_evaluation_pending",
                    work_type_label="Test Evaluation Pending",
                    title=f"{student_name} - '{attempt.test.name}' Evaluation Pending",
                    description=f"Submitted descriptive test '{attempt.test.name}' has ungraded answers.",
                    urgency=urgency,
                    record_id=attempt.id,
                    item_id=f"fac_test_eval_{attempt.id}",
                    created_at=attempt.submitted_at,
                    action_url=f"/internship/instructor/tests/submissions/{attempt.id}/evaluate/",
                    meta={
                        "attempt_id": attempt.id,
                        "test_id": attempt.test_id,
                        "test_name": attempt.test.name,
                        "student_id": attempt.student_id,
                        "student_name": student_name,
                    }
                )

            # =====================================================================
            # 2. TAB: FACULTY ATTENDANCE (Today & Past 7 Days)
            # =====================================================================
            sections = Section.objects.filter(
                batch_id__in=batch_ids,
                class_obj__is_active=True,
                batch__is_active=True,
            ).select_related("class_obj", "batch", "batch__course").prefetch_related("days")

            today_code = self.DAY_CODE_MAP[today.weekday()]
            past_7_days = [today - timedelta(days=d) for d in range(1, 8)]

            existing_sessions = set(
                ClassAttendanceSession.objects.filter(
                    section__in=sections,
                    date__gte=today - timedelta(days=7),
                    date__lte=today,
                ).values_list("section_id", "date")
            )

            for sec in sections:
                sec_day_codes = {d.day for d in sec.days.all()}
                if today_code in sec_day_codes and (sec.id, today) not in existing_sessions:
                    add_item(
                        tab_key="faculty_attendance",
                        work_type="today_attendance_not_marked",
                        work_type_label="Today's Attendance Not Marked",
                        title=f"{sec.class_obj.name} ({sec.batch.batch_number}) - Today's Attendance Pending",
                        description=f"Class scheduled today ({sec.start_time.strftime('%H:%M')} - {sec.end_time.strftime('%H:%M')}) has no attendance marked yet.",
                        urgency="high",
                        record_id=sec.id,
                        item_id=f"fac_att_today_{sec.id}_{today.isoformat()}",
                        due_date=today,
                        action_url=f"/internship/instructor/sections/{sec.id}/attendance/",
                        meta={
                            "section_id": sec.id,
                            "class_name": sec.class_obj.name,
                            "batch_id": sec.batch_id,
                            "batch_number": sec.batch.batch_number,
                            "course_title": sec.batch.course.title,
                            "date": today.isoformat(),
                        }
                    )

                for past_date in past_7_days:
                    if self.DAY_CODE_MAP[past_date.weekday()] in sec_day_codes and (sec.id, past_date) not in existing_sessions:
                        add_item(
                            tab_key="faculty_attendance",
                            work_type="missed_attendance_recent",
                            work_type_label="Missed Attendance (Last 7 Days)",
                            title=f"{sec.class_obj.name} ({sec.batch.batch_number}) - Missed Attendance on {past_date.strftime('%d-%b')}",
                            description=f"Scheduled class on {past_date.strftime('%d-%b-%Y')} has no attendance session recorded.",
                            urgency="medium",
                            record_id=sec.id,
                            item_id=f"fac_att_missed_{sec.id}_{past_date.isoformat()}",
                            due_date=past_date,
                            action_url=f"/internship/instructor/sections/{sec.id}/attendance/",
                            meta={
                                "section_id": sec.id,
                                "class_name": sec.class_obj.name,
                                "batch_id": sec.batch_id,
                                "batch_number": sec.batch.batch_number,
                                "date": past_date.isoformat(),
                            }
                        )

            # =====================================================================
            # 3. TAB: SCHEDULE (Live Classes)
            # =====================================================================
            overdue_live = LiveClass.objects.filter(
                status="scheduled",
                scheduled_start_time__lt=now,
            ).filter(
                Q(faculty_id__in=faculty_ids) | Q(batch_id__in=batch_ids)
            ).select_related("course", "batch").distinct()

            for lc in overdue_live:
                add_item(
                    tab_key="schedule",
                    work_type="overdue_live_class",
                    work_type_label="Overdue Live Class",
                    title=f"Live Class '{lc.title}' - Past Scheduled Time",
                    description=f"Scheduled for {lc.scheduled_start_time.strftime('%d-%b-%Y %H:%M')} but still in 'scheduled' status.",
                    urgency="high",
                    record_id=lc.id,
                    item_id=f"fac_lc_overdue_{lc.id}",
                    created_at=lc.created_at,
                    due_date=lc.scheduled_start_time.date(),
                    action_url=f"/internship/instructor/live-classes/{lc.id}/",
                    meta={
                        "live_class_id": lc.id,
                        "title": lc.title,
                        "course_title": lc.course.title if lc.course else None,
                        "batch_number": lc.batch.batch_number if lc.batch else None,
                        "scheduled_start_time": lc.scheduled_start_time.isoformat(),
                    }
                )

            unended_live = LiveClass.objects.filter(
                status="live",
                scheduled_start_time__lt=now - timedelta(hours=3),
            ).filter(
                Q(faculty_id__in=faculty_ids) | Q(batch_id__in=batch_ids)
            ).select_related("course", "batch").distinct()

            for lc in unended_live:
                add_item(
                    tab_key="schedule",
                    work_type="unended_live_class",
                    work_type_label="Unended Live Class",
                    title=f"Live Class '{lc.title}' - Still Marked Live",
                    description=f"Started over 3 hours ago ({lc.scheduled_start_time.strftime('%d-%b-%Y %H:%M')}) and has not been ended.",
                    urgency="high",
                    record_id=lc.id,
                    item_id=f"fac_lc_unended_{lc.id}",
                    created_at=lc.scheduled_start_time,
                    action_url=f"/internship/instructor/live-classes/{lc.id}/end/",
                    meta={
                        "live_class_id": lc.id,
                        "title": lc.title,
                        "course_title": lc.course.title if lc.course else None,
                    }
                )

            # =====================================================================
            # 4. TAB: FACULTY REPORTS (Draft & Missing Student Reports)
            # =====================================================================
            draft_reports = StudentReport.objects.filter(
                status="draft",
            ).filter(
                Q(faculty_id__in=faculty_ids) | Q(batch_id__in=batch_ids)
            ).select_related("student", "student__profile", "student__profile__user", "batch", "course").distinct()

            for rep in draft_reports:
                student_name = rep.student.profile.user.get_full_name() if rep.student and rep.student.profile and rep.student.profile.user else "Student"
                days_since = (today - rep.created_at.date()).days if rep.created_at else 0
                urgency = "high" if days_since > 5 else "medium"
                add_item(
                    tab_key="faculty_reports",
                    work_type="draft_student_report",
                    work_type_label="Draft Student Report",
                    title=f"{student_name} - Report Still in Draft",
                    description=f"Student report for {rep.course.title} ({rep.batch.batch_number}) has not been submitted.",
                    urgency=urgency,
                    record_id=rep.id,
                    item_id=f"fac_rep_draft_{rep.id}",
                    created_at=rep.created_at,
                    action_url=f"/internship/instructor/reports/{rep.id}/",
                    meta={
                        "report_id": rep.id,
                        "student_id": rep.student_id,
                        "student_name": student_name,
                        "batch_number": rep.batch.batch_number,
                        "course_title": rep.course.title,
                    }
                )

            active_template_course_ids = set(
                ReportTemplate.objects.filter(is_active=True, course_id__in=course_ids).values_list("course_id", flat=True)
            )
            if active_template_course_ids:
                completed_enrollments = StudentCourseEnrollment.objects.filter(
                    batch_id__in=batch_ids,
                    course_id__in=active_template_course_ids,
                    student__status="completed",
                ).select_related("student", "student__profile", "student__profile__user", "batch", "course")

                existing_report_pairs = set(
                    StudentReport.objects.filter(batch_id__in=batch_ids).values_list("student_id", "batch_id")
                )

                for enr in completed_enrollments:
                    if (enr.student_id, enr.batch_id) not in existing_report_pairs:
                        student_name = enr.student.profile.user.get_full_name() if enr.student and enr.student.profile and enr.student.profile.user else "Student"
                        add_item(
                            tab_key="faculty_reports",
                            work_type="missing_student_report",
                            work_type_label="Missing Student Report",
                            title=f"{student_name} - Final Report Missing",
                            description=f"Completed student in {enr.course.title} ({enr.batch.batch_number}) has no student report created.",
                            urgency="high",
                            record_id=enr.student_id,
                            item_id=f"fac_rep_missing_{enr.student_id}_{enr.batch_id}",
                            action_url="/internship/instructor/reports/",
                            meta={
                                "student_id": enr.student_id,
                                "student_name": student_name,
                                "batch_id": enr.batch_id,
                                "batch_number": enr.batch.batch_number,
                                "course_title": enr.course.title,
                            }
                        )

            # =====================================================================
            # 5. TAB: MY COURSES (Draft Tests & Unpublished Recorded Classes)
            # =====================================================================
            draft_tests = Test.objects.filter(
                status="draft",
                batch_id__in=batch_ids,
            ).select_related("course", "batch")

            for t in draft_tests:
                days_since = (today - t.created_at.date()).days if t.created_at else 0
                urgency = "high" if days_since > 3 else "medium"
                add_item(
                    tab_key="my_courses",
                    work_type="draft_test",
                    work_type_label="Draft Test",
                    title=f"Test '{t.name}' - Still in Draft",
                    description=f"Test for {t.course.title} ({t.batch.batch_number}) is in draft and not yet published to students.",
                    urgency=urgency,
                    record_id=t.id,
                    item_id=f"fac_test_draft_{t.id}",
                    created_at=t.created_at,
                    action_url=f"/internship/instructor/tests/{t.id}/",
                    meta={
                        "test_id": t.id,
                        "test_name": t.name,
                        "course_title": t.course.title,
                        "batch_number": t.batch.batch_number,
                    }
                )

            unpublished_recordings = RecordedClass.objects.filter(
                is_published=False,
            ).filter(
                Q(faculty_id__in=faculty_ids) | Q(batch_id__in=batch_ids)
            ).select_related("course", "batch").distinct()

            for rc in unpublished_recordings:
                add_item(
                    tab_key="my_courses",
                    work_type="unpublished_recorded_class",
                    work_type_label="Unpublished Recorded Class",
                    title=f"Recording '{rc.title}' - Not Published",
                    description=f"Recorded class for {rc.course.title} is uploaded but not published.",
                    urgency="low",
                    record_id=rc.id,
                    item_id=f"fac_rec_unpub_{rc.id}",
                    created_at=rc.created_at,
                    action_url=f"/internship/instructor/recorded-classes/{rc.id}/",
                    meta={
                        "recorded_class_id": rc.id,
                        "title": rc.title,
                        "course_title": rc.course.title,
                        "batch_number": rc.batch.batch_number if rc.batch else None,
                    }
                )

            # =====================================================================
            # 6. TAB: FACULTY INTERNS (Overdue Student Tasks)
            # =====================================================================
            overdue_assignments = TaskAssignment.objects.filter(
                status__in=["pending", "revision_required"],
                task__due_date__lt=today,
            ).filter(
                Q(task__batch_id__in=batch_ids) | Q(task__course_id__in=course_ids)
            ).select_related("task", "task__course", "task__batch", "student", "student__profile", "student__profile__user").distinct()

            for assign in overdue_assignments:
                student_name = assign.student.profile.user.get_full_name() if assign.student and assign.student.profile and assign.student.profile.user else "Student"
                days_overdue = (today - assign.task.due_date).days
                urgency = "high" if days_overdue > 3 else "medium"
                add_item(
                    tab_key="faculty_interns",
                    work_type="overdue_student_task",
                    work_type_label="Overdue Student Task",
                    title=f"{student_name} - '{assign.task.title}' Overdue ({days_overdue}d)",
                    description=f"Task due on {assign.task.due_date.strftime('%d-%b-%Y')} is still '{assign.status}'.",
                    urgency=urgency,
                    record_id=assign.id,
                    item_id=f"fac_intern_overdue_{assign.id}",
                    created_at=assign.assigned_at,
                    due_date=assign.task.due_date,
                    action_url=f"/internship/instructor/tasks/{assign.task_id}/detail/",
                    meta={
                        "assignment_id": assign.id,
                        "task_id": assign.task_id,
                        "task_title": assign.task.title,
                        "student_id": assign.student_id,
                        "student_name": student_name,
                        "days_overdue": days_overdue,
                    }
                )

        # =========================================================================
        # BUILD TAB METADATA & FILTERING
        # =========================================================================
        tab_counts = {tab["key"]: len(tab_items[tab["key"]]) for tab in self.TAB_DEFINITIONS}
        total_pending_count = sum(tab_counts.values())

        tabs_data = []
        for tab_def in self.TAB_DEFINITIONS:
            k = tab_def["key"]
            tabs_data.append({
                "key": k,
                "label": tab_def["label"],
                "count": tab_counts[k],
                "categories": list(tab_categories[k].values()),
            })

        if active_tab in tab_items:
            combined_items = tab_items[active_tab]
        else:
            active_tab = "all"
            combined_items = []
            for k in [t["key"] for t in self.TAB_DEFINITIONS]:
                combined_items.extend(tab_items[k])

        if urgency_filter in ["high", "medium", "low"]:
            combined_items = [it for it in combined_items if it["urgency"] == urgency_filter]

        if search_query:
            combined_items = [
                it for it in combined_items
                if search_query in it["title"].lower()
                or search_query in it["description"].lower()
                or search_query in str(it.get("meta", {})).lower()
            ]

        urgency_priority = {"high": 1, "medium": 2, "low": 3}
        combined_items.sort(key=lambda x: urgency_priority.get(x["urgency"], 4))

        if limit_param.isdigit():
            limit_val = int(limit_param)
            if limit_val > 0:
                combined_items = combined_items[:limit_val]

        response_data = {
            "module": "faculty",
            "module_label": "Faculty Management",
            "total_pending_count": total_pending_count,
            "tab_counts": tab_counts,
            "tabs": tabs_data,
            "active_tab": active_tab,
            "items_count": len(combined_items),
            "items": combined_items,
        }

        serializer = AcademicPendingDashboardSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
