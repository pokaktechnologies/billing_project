from django.shortcuts import get_object_or_404
from rest_framework import generics,filters, status
from rest_framework.response import Response
from internship.models import Course, Student, Faculty
from internship.serializers.instructor import CourseSerializer
from internship.models import AssignedStaffCourse
from internship.serializers.instructor import *
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q
from attendance.models import DailyAttendance
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
from datetime import timedelta
from rest_framework.filters import SearchFilter
from accounts.models import StaffProfile
from internship.serializers.internship_admin import StudentSerializer


# ===== Course Views ======
class InstructorCourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = Course.objects.prefetch_related("installments", "department").order_by('-created_at')
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]



class InstructorCourseRetrieveUpdateDestroyAPIView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = Course.objects.prefetch_related("installments", "department")
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]



# class InstallmentListAPIView(generics.ListAPIView):
#     serializer_class = CourseInstallmentSerializer
#     permission_classes = [IsAuthenticated]


#     def get_queryset(self):
#         course_id = self.kwargs.get("course_id")
#         return InstallmentPlan.objects.filter(course_id=course_id).order_by("due_days")


class InstructorAssignedStaffCourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = AssignedStaffCourse.objects.select_related("staff", "course").order_by("-assigned_date")
    permission_classes = [IsAuthenticated]


    def get_serializer_class(self):
        if self.request.method == "POST":
            return AssignedStaffCourseCreateSerializer
        return AssignedStaffCourseSerializer

    def create(self, request, *args, **kwargs):
        serializer = AssignedStaffCourseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_objects = serializer.save()

        # return full details
        data = AssignedStaffCourseSerializer(created_objects, many=True).data
        return Response(data, status=201)


class InstructorAssignedStaffCourseRetrieveUpdateDestroyAPIView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = AssignedStaffCourse.objects.select_related("staff", "course")
    serializer_class = AssignedStaffCourseDetailSerializer
    permission_classes = [IsAuthenticated]



#list staff inter by course id (Enrolled Students(count))
class CourseEnrolledStudentsListAPIView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request, course_id):

        #search by student name
        student_name_search = request.query_params.get("student_name")

        #filter by enrollment date range
        enrollment_date_from = request.query_params.get("date_from")
        enrollment_date_to = request.query_params.get("date_to")

        #filter by course
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=404)

        assigned_staff_courses = AssignedStaffCourse.objects.filter(course=course).select_related("staff__user")

        #search by student name (first name) if query param provided
        if student_name_search:
            assigned_staff_courses = assigned_staff_courses.filter(
                staff__user__first_name__icontains=student_name_search
            )

        #filter by enrollment date range if query params provided
        if enrollment_date_from:
            assigned_staff_courses = assigned_staff_courses.filter(assigned_date__gte=enrollment_date_from)
        if enrollment_date_to:
            assigned_staff_courses = assigned_staff_courses.filter(assigned_date__lte=enrollment_date_to)

        serializer = AssignedStaffCourseSerializer(assigned_staff_courses, many=True)
        return Response(
            {
                 "enrolled_students_count": assigned_staff_courses.count(),
                "enrolled_students": serializer.data,
            }
        )


# ===== Intern Views ======

class StudentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        course_id = request.query_params.get("course")
        name = request.query_params.get("name")
        status = request.query_params.get("status")
        batch_id = request.query_params.get("batch")

        qs = Student.objects.select_related(
            "profile__user",
            "course",
            "batch",
            "center"
        )

        # batch filter
        if batch_id:
            qs = qs.filter(batch_id=batch_id)

        # course filter
        if course_id:
            qs = qs.filter(course_id=course_id)

        # active/inactive
        if status:

            if status == "active":
                qs = qs.filter(is_active=True)
            elif status == "inactive":
                qs = qs.filter(is_active=False)

        # name filter
        if name:
            qs = qs.filter(
                Q(profile__user__first_name__icontains=name) |
                Q(profile__user__last_name__icontains=name) |
                Q(profile__user__email__icontains=name)
            )

        serializer = StudentSerializer(qs, many=True)
        return Response(serializer.data)


class StudentProfileInfoAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    serializer_class = StudentSerializer
    queryset = Student.objects.select_related(
        "profile__user",
        "course",
        "batch",
        "center",
        "payment_type",
        "councellor"
    )


class StudentsStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        students = Student.objects.all()

        total = students.count()
        active = students.filter(is_active=True).count()
        inactive = students.filter(is_active=False).count()

        return Response({
            "total_students": total,
            "active_students": active,
            "inactive_students": inactive,
        })



# ====== Study Material ViewSet ======

class StudyMaterialAPIView(generics.ListCreateAPIView):
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['course', 'batches', 'material_type']
    search_fields = ['title', 'description']


class StudyMaterialDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated]



# list study materials by course
class CourseStudyMaterialListAPIView(generics.ListAPIView):
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        batch_id = self.kwargs.get("batch_id")

        title = self.request.query_params.get("title")
        material_type = self.request.query_params.get("type")

        queryset = StudyMaterial.objects.all()

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        if batch_id:
            queryset = queryset.filter(batches__id=batch_id)

        if title:
            queryset = queryset.filter(title__icontains=title)

        if material_type:
            queryset = queryset.filter(material_type=material_type)

        return queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        })


# ===== Task Views ======

from internship.models import Task
class TaskListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all().order_by('-id')

    def get_queryset(self):
        qs = Task.objects.all().order_by('-id')

        title = self.request.query_params.get("title")
        student_ids = self.request.query_params.get("student")  # ✅ renamed
        course = self.request.query_params.get("course")
        batch = self.request.query_params.get("batch")
        status = self.request.query_params.get("status")  # pending, submitted, revision_required, completed

        assigned_from = self.request.query_params.get("assigned_from")
        assigned_to = self.request.query_params.get("assigned_to")

        due_from = self.request.query_params.get("due_from")
        due_to = self.request.query_params.get("due_to")

        if course:
            qs = qs.filter(course_id=course)

        if batch:
            qs = qs.filter(batch_id=batch)

        if title:
            qs = qs.filter(title__icontains=title)

        # ✅ student-based filtering
        if student_ids:
            student_ids = [int(x) for x in student_ids.split(",") if x.isdigit()]

            qs = qs.filter(assignments__student_id__in=student_ids)

            if status:
                qs = qs.filter(assignments__status=status)

            if assigned_from:
                qs = qs.filter(assignments__assigned_at__date__gte=assigned_from)

            if assigned_to:
                qs = qs.filter(assignments__assigned_at__date__lte=assigned_to)

            if due_from:
                qs = qs.filter(assignments__revision_due_date__gte=due_from)

            if due_to:
                qs = qs.filter(assignments__revision_due_date__lte=due_to)

        return qs.distinct()


class TaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

class TaskDetailAPIView(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = InstructorTaskDetailSerializer
    permission_classes = [IsAuthenticated]


class BatchTaskListAPIView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        batch_id = self.kwargs.get("batch_id")
        return Task.objects.filter(batch_id=batch_id).order_by('-id')


class TaskAttachmentDeleteAPIView(generics.DestroyAPIView):
    queryset = TaskAttachment.objects.all()
    permission_classes = [IsAuthenticated]


class TaskStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        from django.db import models

        total_tasks = Task.objects.count()
        total_task_assignments = TaskAssignment.objects.count()   # <-- THIS

        status_counts = (
            TaskAssignment.objects
            .values('status')
            .annotate(count=models.Count('id'))
        )

        stats = {
            "total_tasks": total_tasks,
            "total_task_assignments": total_task_assignments,   # <-- ADDED
            "pending": 0,
            "submitted": 0,
            "revision_required": 0,
            "completed": 0,
        }

        for row in status_counts:
            stats[row["status"]] = row["count"]

        return Response(stats)


class StudentPerformanceStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        qs = TaskAssignment.objects.filter(student_id=student_id)

        total = qs.count()
        completed = qs.filter(status="completed").count()
        pending = qs.filter(status="pending").count()
        submitted = qs.filter(status="submitted").count()
        revision = qs.filter(status="revision_required").count()

        # ---- Attendance (if students have attendance) ----
        attendance_qs = DailyAttendance.objects.filter(staff=student_id)

        total_days = attendance_qs.count()

        if total_days > 0:
            full_days = attendance_qs.filter(status="full_day").count()
            half_days = attendance_qs.filter(status="half_day").count()

            attend_score = full_days * 1 + half_days * 0.5
            attendance_percentage = round((attend_score / total_days) * 100, 2)
        else:
            attendance_percentage = None

        # ---- Performance Status ----
        if attendance_percentage is None:
            performance_status = "No attendance data"
        elif attendance_percentage >= 90:
            performance_status = "Excellent"
        elif 75 <= attendance_percentage < 90:
            performance_status = "Good"
        elif 50 <= attendance_percentage < 75:
            performance_status = "Average"
        else:
            performance_status = "Poor"

        return Response({
            "group1": {
                "tasks_completed": completed,
            },
            "group2": {
                "pending_tasks": pending,
            },
            "group3": {
                "attendance_percentage": attendance_percentage,
                "performance_status": performance_status,
            }
        })

from django.db.models import Subquery, OuterRef, F
from django.utils.timezone import now

from collections import defaultdict
from django.utils.timezone import now

class InternTaskStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id, format=None):

        # 🔹 pull ALL assignments for that student
        assignments = (
            TaskAssignment.objects
            .filter(student_id=student_id)
            .select_related("task")
            .order_by("task_id", "-assigned_at")
        )

        # 🔹 pick latest assignment per task
        latest_by_task = {}
        for a in assignments:
            if a.task_id not in latest_by_task:
                latest_by_task[a.task_id] = a

        latest = latest_by_task.values()

        # 🔹 counts
        total_tasks = len(latest)
        completed = sum(1 for a in latest if a.status == "completed")
        pending = sum(1 for a in latest if a.status == "pending")
        submitted = sum(1 for a in latest if a.status == "submitted")
        revision = sum(1 for a in latest if a.status == "revision_required")

        # 🔹 overdue check
        today = now().date()
        overdue = sum(
            1 for a in latest
            if a.task.due_date < today and a.status != "completed"
        )

        return Response({
            "total_tasks": total_tasks,
            "pending": pending,
            "submitted": submitted,
            "revision_required": revision,
            "completed": completed,
            "overdue": overdue,
        })


# ===== Submission Views ======

class InstructorSubmissionListAPIView(generics.ListAPIView):
    serializer_class = InstructorSubmissionSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        qs = TaskSubmission.objects.select_related(
            "assignment__task",
            "assignment__student__profile__user",
            "assignment__staff__user"
        )

        title = self.request.query_params.get("title")
        student = self.request.query_params.get("student")
        status = self.request.query_params.get("status")
        search = self.request.query_params.get("search")

        # 🔹 title filter
        if title:
            qs = qs.filter(assignment__task__title__icontains=title)

        # 🔹 status filter
        if status:
            qs = qs.filter(assignment__status=status)

        # 🔹 student filter (hybrid)
        if student:
            if student.isdigit():
                qs = qs.filter(
                    Q(assignment__student_id=int(student)) |
                    Q(assignment__staff_id=int(student))
                )
            else:
                qs = qs.filter(
                    Q(assignment__student__profile__user__first_name__icontains=student) |
                    Q(assignment__student__profile__user__last_name__icontains=student) |
                    Q(assignment__student__profile__user__email__icontains=student) |
                    Q(assignment__staff__user__first_name__icontains=student) |
                    Q(assignment__staff__user__last_name__icontains=student) |
                    Q(assignment__staff__user__email__icontains=student)
                )

        # 🔍 GLOBAL SEARCH (title + student name)
        if search:
            qs = qs.filter(
                Q(assignment__task__title__icontains=search) |
                Q(assignment__student__profile__user__first_name__icontains=search) |
                Q(assignment__student__profile__user__last_name__icontains=search) |
                Q(assignment__staff__user__first_name__icontains=search) |
                Q(assignment__staff__user__last_name__icontains=search)
            )

        return qs.order_by("-id").distinct()


# detail view to review a submission
class InstructorSubmissionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = InstructorSubmissionDetailSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        return TaskSubmission.objects.all()

class InstructorSubmissionReviewAPI(generics.UpdateAPIView):
    serializer_class = InstructorSubmissionReviewSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        return TaskSubmission.objects.all()


class SubmissionStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        # Get all task assignments (each assignment represents one staff-task pair)
        assignments = TaskAssignment.objects.all()

        stats = {
            "total_assignments": assignments.count(),
            "pending": 0,
            "submitted": 0,
            "revision_required": 0,
            "completed": 0,
        }

        for assignment in assignments:
            # Use assignment.status, because the status lives here — not in submissions
            status = assignment.status

            # Validate status exists in stats (just safety)
            if status in stats:
                stats[status] += 1

        return Response(stats)

# course under the faculy
class FacultyCourseListAPIView(APIView):
    def get(self, request, faculty_id):
        courses = Course.objects.filter(
            batches__faculties__id=faculty_id,
            is_active=True
        ).select_related(
            "department", "tax_settings"
        ).prefetch_related(
            "batches__faculties",
            "installment_plans__items"
        ).distinct()

        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FacultyStudentsAPIView(APIView):

    def get(self, request, faculty_id):
        try:
            faculty = Faculty.objects.get(id=faculty_id)
        except Faculty.DoesNotExist:
            return Response({"error": "Faculty not found"}, status=404)

        # Get batches handled by faculty
        batches = faculty.batches.all()

        # Get students in those batches
        students = Student.objects.filter(batch__in=batches)

        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)