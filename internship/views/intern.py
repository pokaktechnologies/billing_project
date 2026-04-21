from django.db.models import Sum

from rest_framework import generics, serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Course, CoursePayment, StudyMaterial, Task, TaskAssignment, TaskSubmissionAttachment
from ..serializers import internship_admin
from ..serializers.intern import (
    InternTaskMiniSerializer,
    InternTaskSerializer,
    StudyMaterialMiniSerializer,
    TaskSubmissionAttachmentSerializer,
    TaskSubmissionSerializer,
)
from ..serializers.instructor import StudyMaterialSerializer
from ..serializers.internship_admin import CoursePaymentDetailSerializer
from ..utils import (
    get_authenticated_student,
    get_student_course_ids,
    get_student_courses_queryset,
    get_student_enrollments,
    get_student_submissions_queryset,
    get_student_task_assignments,
    get_student_tasks_queryset,
)


# === Course Views ===

class MyCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = get_authenticated_student(request.user)
        if not student:
            return Response(
                {"detail": "User has no student profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        courses = list(get_student_courses_queryset(student))
        serializer = internship_admin.CourseSerializer(courses, many=True)
        data = serializer.data

        for course_data, course in zip(data, courses):
            course_data["study_material_count"] = course.study_material_count

        return Response(data)


class MyCourseDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = internship_admin.CourseSerializer

    def get_queryset(self):
        student = get_authenticated_student(self.request.user)
        return get_student_courses_queryset(student)


class MyCourseStudyMaterialListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudyMaterialSerializer

    def get_queryset(self):
        student = get_authenticated_student(self.request.user)
        if not student:
            return StudyMaterial.objects.none()

        course_id = self.kwargs.get("course_id")
        queryset = StudyMaterial.objects.filter(
            course_id__in=get_student_course_ids(student),
            is_public=True,
        ).select_related("course")

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        title = self.request.query_params.get("title")
        if title:
            queryset = queryset.filter(title__icontains=title)

        material_type = self.request.query_params.get("type")
        if material_type:
            queryset = queryset.filter(material_type=material_type)

        return queryset.order_by("-created_at")


class MyStudyMaterialDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudyMaterialSerializer

    def get_queryset(self):
        student = get_authenticated_student(self.request.user)
        if not student:
            return StudyMaterial.objects.none()

        return StudyMaterial.objects.filter(
            is_public=True,
            course_id__in=get_student_course_ids(student),
        ).select_related("course")


# === Task Views ===

class MyTaskViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InternTaskSerializer

    def get_queryset(self):
        student = get_authenticated_student(self.request.user)
        if not student:
            return Task.objects.none()

        queryset = get_student_tasks_queryset(student)

        title = self.request.query_params.get("title")
        status_filter = self.request.query_params.get("status")

        if title:
            queryset = queryset.filter(title__icontains=title)

        if status_filter:
            queryset = queryset.filter(latest_status=status_filter)

        return queryset.order_by("-id")


class MyTaskStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = get_authenticated_student(request.user)
        if not student:
            return Response({"detail": "Student profile not found."}, status=400)

        tasks = get_student_tasks_queryset(student)

        data = {
            "all_tasks": tasks.count(),
            "pending": tasks.filter(latest_status="pending").count(),
            "submitted": tasks.filter(latest_status="submitted").count(),
            "approved": tasks.filter(latest_status="completed").count(),
            "revision": tasks.filter(latest_status="revision_required").count(),
        }

        return Response(data)


# === Task Submission Views ===

class TaskSubmissionListCreateAPI(generics.ListCreateAPIView):
    serializer_class = TaskSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        student = get_authenticated_student(self.request.user)
        queryset = get_student_submissions_queryset(student)

        task_id = self.request.query_params.get("task_id")
        if task_id:
            queryset = queryset.filter(assignment__task__id=task_id)

        return queryset

    def perform_create(self, serializer):
        assignment_id = self.request.data.get("assignment")
        student = get_authenticated_student(self.request.user)

        if not student:
            raise serializers.ValidationError("User has no student profile.")

        if not assignment_id:
            raise serializers.ValidationError({"assignment": "Assignment is required."})

        try:
            assignment = get_student_task_assignments(student).get(id=assignment_id)
        except TaskAssignment.DoesNotExist:
            raise serializers.ValidationError("You are not assigned to this task.")

        serializer.save(assignment=assignment)


class TaskSubmissionDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        student = get_authenticated_student(self.request.user)
        return get_student_submissions_queryset(student)


class DeleteTaskSubmissionAttachmentAPI(generics.DestroyAPIView):
    serializer_class = TaskSubmissionAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        student = get_authenticated_student(self.request.user)
        if not student:
            return TaskSubmissionAttachment.objects.none()

        return TaskSubmissionAttachment.objects.filter(
            submission__assignment__student=student
        ).select_related("submission", "submission__assignment")


class MyCoursePaymentListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = get_authenticated_student(request.user)
        if not student:
            return Response(
                {"detail": "User has no student profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course_id = request.query_params.get("course_id")
        payment_qs = (
            CoursePayment.objects
            .filter(student=student)
            .select_related(
                "student",
                "student__profile",
                "student__profile__user",
                "installments",
                "installments__plan",
                "installments__plan__course",
            )
            .order_by("-payment_date", "-id")
        )

        if course_id:
            if not get_student_enrollments(student).filter(course_id=course_id).exists():
                return Response(
                    {"detail": "Course not found in your enrollments"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            payment_qs = payment_qs.filter(installments__plan__course_id=course_id)

        payment = payment_qs.first()
        if not payment:
            return Response(
                {"detail": "No payments found for this student"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CoursePaymentDetailSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)


# === Dashboard ===

class InternDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = get_authenticated_student(request.user)
        if not student:
            return Response(
                {"detail": "Student profile not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tasks_qs = get_student_tasks_queryset(student).order_by("-id")
        task_stats = {
            "total": tasks_qs.count(),
            "pending": tasks_qs.filter(latest_status="pending").count(),
            "submitted": tasks_qs.filter(latest_status="submitted").count(),
            "completed": tasks_qs.filter(latest_status="completed").count(),
            "revision": tasks_qs.filter(latest_status="revision_required").count(),
        }

        latest_tasks = InternTaskMiniSerializer(tasks_qs[:5], many=True).data

        study_materials_qs = (
            StudyMaterial.objects
            .filter(
                course_id__in=get_student_course_ids(student),
                is_public=True,
            )
            .select_related("course")
            .order_by("-created_at")
            .distinct()[:5]
        )
        study_materials = StudyMaterialMiniSerializer(study_materials_qs, many=True).data

        payments_qs = CoursePayment.objects.filter(student=student)
        total_paid = payments_qs.aggregate(total=Sum("amount_paid"))["total"] or 0

        total_fee = (
            Course.objects
            .filter(enrollments__student=student)
            .distinct()
            .aggregate(total=Sum("total_fee"))["total"]
        ) or 0
        balance = total_fee - total_paid

        payment_summary = {
            "total_fee": total_fee,
            "paid_amount": total_paid,
            "balance_amount": balance,
            "status": "Paid" if balance <= 0 else "Pending",
        }

        return Response({
            "status": "success",
            "message": "Intern dashboard data fetched successfully",
            "data": {
                "task_stats": task_stats,
                "latest_tasks": latest_tasks,
                "study_materials": study_materials,
                "payments": payment_summary,
            },
        })
