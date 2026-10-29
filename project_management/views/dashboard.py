from datetime import date
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from attendance.models import DailyAttendance
from attendance.serializers import DailyAttendanceSessionDetailSerializer
from ..models import ClientContract, ProjectManagement, TaskAssign
from ..serializers import AssignedTaskListSerializer, ProjectManagerSerializer


class ProjectManagerDashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        staff_profile = getattr(user, 'staff_profile', None)

        if not staff_profile:
            return Response(
                {"status": "0", "message": "No staff profile found"},
                status=status.HTTP_403_FORBIDDEN
            )

        job_detail = getattr(staff_profile, 'job_detail', None)
        if not job_detail:
            return Response(
                {"status": "0", "message": "No job detail found"},
                status=status.HTTP_403_FORBIDDEN
            )

        # -----------------------------
        # PROJECTS OWNED BY PM
        # -----------------------------
        total_projects = ProjectManagement.objects.filter(user=user).order_by("-created_at")

        active_projects_count = total_projects.filter(status__in=["not_started", "in_progress", "on_hold"]).count()

        # -----------------------------
        # TASK ASSIGNMENTS BY PM
        # -----------------------------
        assigned_tasks = TaskAssign.objects.select_related(
            "task",
            "assigned_to__member",
            "assigned_to__project"
        ).filter(assigned_by=user).order_by("-assigned_at")

        submitted_tasks = assigned_tasks.filter(task__status="completed")

        completed_tasks = assigned_tasks.filter(task__status="completed").count()

        pending_tasks = assigned_tasks.filter(
            task__status__in=["not_started", "in_progress", "on_hold"]).count()

        overdue_tasks = assigned_tasks.filter(
            task__end_date__lt=date.today(),
            task__status__in=["not_started", "in_progress", "on_hold"]).count()

        # -----------------------------
        # SERIALIZERS
        # -----------------------------
        project_serializer = ProjectManagerSerializer(total_projects[:3], many=True)

        assigned_task_serializer = AssignedTaskListSerializer(assigned_tasks[:3], many=True)
        submitted_tasks_serializer = AssignedTaskListSerializer(submitted_tasks[:3], many=True)

        today = timezone.localdate()
        today_attendance = DailyAttendance.objects.filter(
            staff=staff_profile,
            date=today
        ).first()
        if today_attendance:
            attendance = DailyAttendanceSessionDetailSerializer(today_attendance).data
        else:
            attendance = None

        user_data = {
            "employee_id": job_detail.employee_id,
            "job_type": job_detail.job_type,
            "role": job_detail.role,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}",
        }

        # -----------------------------
        # RESPONSE
        # -----------------------------
        return Response(
            {
                "status": "1",
                "message": "success",
                "data": {
                    "user": user_data,
                    "stats": {
                        "total_projects": active_projects_count,
                        "completed_tasks": completed_tasks,
                        "pending_tasks": pending_tasks,
                        "overdue_tasks": overdue_tasks,
                    },
                    "projects": project_serializer.data,
                    "assigned_tasks": assigned_task_serializer.data,
                    "submitted_tasks": submitted_tasks_serializer.data,
                    'attendance': attendance,
                }
            },
            status=status.HTTP_200_OK
        )


class NumberGeneratorView(APIView):
    def generate_next_number(self, model, field_name: str, prefix: str, length: int) -> str:
        start = 10**(length - 1) + 1  # e.g., for length 6 -> 100001

        # Filter by prefix and order descending to get the latest number
        latest_order = model.objects.filter(**{f"{field_name}__startswith": f"{prefix}|"}).order_by(f"-{field_name}").first()

        if latest_order:
            latest_number_str = getattr(latest_order, field_name).split('|')[1]
            next_number = int(latest_number_str) + 1
        else:
            next_number = start  # Start from e.g., 100001

        return f"{prefix}|{next_number:0{length}d}"

    def get(self, request):
        req_type = request.query_params.get('type') or request.query_params.get('type ')
        if isinstance(req_type, str):
            req_type = req_type.strip().upper()

        if req_type == "PR":
            generated_number = self.generate_next_number(ProjectManagement, "project_number", "PR", 6)
        elif req_type == "CN":
            generated_number = self.generate_next_number(ClientContract, "contract_number", "CN", 6)
        else:
            return Response({
                'status': '0',
                'message': 'Invalid type.',
                'number': None
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': '1',
            'message': 'Success',
            'number': generated_number
        }, status=status.HTTP_200_OK)
