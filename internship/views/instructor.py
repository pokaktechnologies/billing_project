from rest_framework import generics
from rest_framework.response import Response
from internship.models import Course
from internship.serializers.instructor import CourseSerializer
from internship.models import AssignedStaffCourse
from internship.serializers.instructor import *
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q
from attendance.models import DailyAttendance

# ===== Course Views ======
class InstructorCourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

class InstructorCourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"


class InstructorAssignedStaffCourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = AssignedStaffCourse.objects.select_related("staff", "course").order_by("-assigned_date")
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

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
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"


#list staff inter by course id (Enrolled Students(count))
class CourseEnrolledStudentsListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=404)
        
        assigned_staff_courses = AssignedStaffCourse.objects.filter(course=course).select_related("staff__user")
        serializer = AssignedStaffCourseSerializer(assigned_staff_courses, many=True)
        return Response(
            {
                 "enrolled_students_count": assigned_staff_courses.count(),
                "enrolled_students": serializer.data,
            }
        )


# ===== Intern Views ======

class InternListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

    def get(self, request):
        department_id = request.query_params.get("department")    # int
        name = request.query_params.get("name")                   # str
        status = request.query_params.get("status")               # active, inactive, etc.

        qs = JobDetail.objects.filter(job_type="internship").select_related(
            "staff", "staff__user", "department"
        )

        # department filter
        if department_id:
            qs = qs.filter(department_id=department_id)

        # status filter
        if status:
            qs = qs.filter(status=status)

        # name filter (first, last, or email)
        if name:
            qs = qs.filter(
                Q(staff__user__first_name__icontains=name) |
                Q(staff__user__last_name__icontains=name) |
                Q(staff__user__email__icontains=name)
            )

        # output staff profile, not jobdetail itself
        staff_profiles = [item.staff for item in qs]

        serializer = StaffProfileSerializer(staff_profiles, many=True)
        return Response(serializer.data)

class InternsStatsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

    def get(self, request, *args, **kwargs):
        # interns = job_detail rows where job_type == internship
        interns = JobDetail.objects.filter(job_type="internship")

        total_interns = interns.count()
        active = interns.filter(status="active").count()
        inactive = interns.filter(status="inactive").count()

        return Response({
            "total_interns": total_interns,
            "active_interns": active,
            "inactive_interns": inactive,
        })




# ====== Study Material ViewSet ======

class StudyMaterialAPIView(generics.ListCreateAPIView):
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

class StudyMaterialDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"


# list study materials by course
class CourseStudyMaterialListAPIView(generics.ListAPIView):
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")

        title = self.request.query_params.get("title")
        material_type = self.request.query_params.get("type") 

        queryset = StudyMaterial.objects.filter(course=course_id).order_by("-created_at")

        if title:
            queryset = queryset.filter(title__icontains=title)

        if material_type:
            queryset = queryset.filter(material_type=material_type)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        })


# ===== Task Views ======

class TaskListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all().order_by('-id')

    def get_queryset(self):
        qs = Task.objects.all().order_by('-id')

        title = self.request.query_params.get("title")
        intern_ids = self.request.query_params.get("intern")
        course = self.request.query_params.get("course")

        if course:
            qs =  qs.filter(course_id=course)

        if title:
            qs = qs.filter(title__icontains=title)

        if intern_ids:
            staff_ids = [int(x) for x in intern_ids.split(",") if x.isdigit()]
            qs = qs.filter(assignments__staff_id__in=staff_ids).distinct()

        return qs
class TaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

class TaskDetailAPIView(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = InstructorTaskDetailSerializer
    permission_classes = [IsAuthenticated]


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


class StaffPerformanceStatsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

    def get(self, request, staff_id):
        qs = TaskAssignment.objects.filter(staff_id=staff_id)

        total = qs.count()
        completed = qs.filter(status="completed").count()
        pending = qs.filter(status="pending").count()
        submitted = qs.filter(status="submitted").count()
        revision = qs.filter(status="revision_required").count()


        # ---- Attendance calculation ----
        attendance_qs = DailyAttendance.objects.filter(staff_id=staff_id)

        total_days = attendance_qs.count()

        if total_days > 0:
            full_days = attendance_qs.filter(status="full_day").count()
            half_days = attendance_qs.filter(status="half_day").count()

            attend_score = full_days * 1 + half_days * 0.5
            attendance_percentage = round((attend_score / total_days) * 100, 2)
        else:
            attendance_percentage = None   # no data
        
        # ---- Performance Status (based on attendance) ----
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

    def get(self, request, staff_id, format=None):
        # pull ALL assignments for that staff
        assignments = (
            TaskAssignment.objects
            .filter(staff_id=staff_id)
            .select_related("task")
            .order_by("task_id", "-assigned_at")
        )

        # pick latest per task
        latest_by_task = {}
        for a in assignments:
            if a.task_id not in latest_by_task:
                latest_by_task[a.task_id] = a

        # now we have exactly 1 assignment per task
        latest = latest_by_task.values()

        # counts
        total_tasks = len(latest)
        completed = sum(1 for a in latest if a.status == "completed")
        pending = sum(1 for a in latest if a.status == "pending")
        submitted = sum(1 for a in latest if a.status == "submitted")
        revision = sum(1 for a in latest if a.status == "revision_required")

        # overdue check
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
        return TaskSubmission.objects.all()


# detail view to review a submission
class InstructorSubmissionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = InstructorSubmissionSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        return TaskSubmission.objects.all()

class InstructorSubmissionReviewAPI(generics.UpdateAPIView):
    serializer_class = InstructorSubmissionReviewSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        return TaskSubmission.objects.all()