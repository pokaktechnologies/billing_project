from datetime import datetime, date, timedelta
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_logs.base_view import BaseAPIView, BaseGenericAPIView
from ..models import (
    Task,
    TaskBoard,
    StatusColumns,
    TaskAssign,
    ProjectMember,
    ProjectManagement,
    Member,
)
from ..serializers import (
    TaskBoardSerializer,
    StatusColumnWithTasksSerializer,
    TaskSerializer,
    TaskAssignSerializer,
)
from .pagination import ReportPagination

class TaskBoardListByProjectView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        boards = TaskBoard.objects.filter(project__id=project_id).order_by('-created_at')
        serializer = TaskBoardSerializer(boards, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

#My Projects

from django.db.models import Count, Q



# Task views


#Create Board
class CreateListBoard(BaseGenericAPIView, generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = TaskBoard.objects.all().order_by('-updated_at')
    serializer_class = TaskBoardSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

class ListBoardMember(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = TaskBoardSerializer

    def get_queryset(self):
        return TaskBoard.objects.filter(
            project__projectmember__member__user=self.request.user
        ).select_related('project').distinct().order_by('-updated_at')
    
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

class DistroyUpdateBoard(BaseGenericAPIView, generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = TaskBoard.objects.all()
    serializer_class = TaskBoardSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Set board to null for all tasks associated with this board
        Task.objects.filter(board=instance).update(board=None)
        return super().destroy(request, *args, **kwargs)

class CreateStatusColumn(BaseGenericAPIView, generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    serializer_class = StatusColumnWithTasksSerializer

    def get_queryset(self):
        board_id = self.request.query_params.get('board')

        qs = StatusColumns.objects.prefetch_related(
            'task_set'
        ).order_by('id')

        if board_id:
            qs = qs.filter(board_id=board_id)

        return qs


class DistroyUpdateStatusColumn(BaseGenericAPIView, generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = StatusColumns.objects.all()
    serializer_class = StatusColumnWithTasksSerializer


class TaskListCreateView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

    def get(self, request):
        project = request.query_params.get('project')
        board = request.query_params.get('board')
        status_filter = request.query_params.get('status')

        task = Task.objects.all().order_by('-created_at')

        # project filter
        if project:
            task = task.filter(project__id=project)

        # board filter
        if board:
            task = task.filter(board__id=board)

        # allowed status filter
        allowed_status = ['not_started', 'in_progress', 'completed']
        if status_filter in allowed_status:
            task = task.filter(status=status_filter)

        serializer = TaskSerializer(task, many=True)

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = TaskSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"status": "0", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        assigned_to = request.data.get("assigned_to")
        if not assigned_to:
            return Response(
                {"status": "0", "message": "assigned_to field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project_member = ProjectMember.objects.filter(pk=assigned_to).first()
        if not project_member:
            return Response(
                {"status": "0", "message": "Project member not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        print("VALIDATED DATA:", serializer.validated_data)

        with transaction.atomic():
            task = serializer.save()

            TaskAssign.objects.create(
                task=task,
                assigned_by=request.user,
                assigned_to=project_member
            )

        return Response(
            {"status": "1", "message": "Task created successfully"},
            status=status.HTTP_201_CREATED
        )
    
#MyProject Tasks
class MyProjectTaskListView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id=None):
        user = request.user
        project_id = request.query_params.get("project")
        board_id = request.query_params.get("board")
        status_filter = request.query_params.get("status")

        tasks = Task.objects.filter(
            assignments__assigned_to__member__user=user
        )

        # optional board filter
        if board_id:
            tasks = tasks.filter(board_id=board_id)

        # optional project filter
        if project_id:
            tasks = tasks.filter(project_id=project_id)
        
        # allowed status filter
        allowed_status = ['not_started', 'in_progress', 'completed']
        if status_filter in allowed_status:
            tasks = tasks.filter(status=status_filter)


        tasks = tasks.select_related(
            'project', 'board'
        ).prefetch_related(
            'assignments'
        ).distinct().order_by('-created_at')

        # retrieve single task
        if task_id:
            task = tasks.filter(id=task_id).first()
            if not task:
                return Response(
                    {"status": "0", "message": "Task not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = TaskSerializer(task)
            return Response(
                {"status": "1", "data": serializer.data},
                status=status.HTTP_200_OK
            )

        serializer = TaskSerializer(tasks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )
    
    def patch(self, request, task_id):
        user = request.user

        task = Task.objects.filter(
            id=task_id,
            assignments__assigned_to__member__user=user
        ).first()

        if not task:
            return Response(
                {
                    "status": "0",
                    "message": "Task not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        allowed_status = [
            'not_started',
            'in_progress',
            'completed'
        ]

        new_status = request.data.get("status")

        if new_status and new_status not in allowed_status:
            return Response(
                {
                    "status": "0",
                    "message": "Invalid status"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        protected_fields = [
            "project",
            "board",
            "start_time",
            "end_time",
            "duration",
        ]

        for field in protected_fields:
            if field in request.data:
                return Response(
                    {
                        "status": "0",
                        "message": f"{field} cannot be updated"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        old_status = task.status

        with transaction.atomic():

            # --------------------------------------
            # START TASK
            # not_started -> in_progress
            # --------------------------------------
            if (
                old_status == 'not_started'
                and new_status == 'in_progress'
            ):
                if task.start_time is None:
                    task.start_time = timezone.now()

            # --------------------------------------
            # COMPLETE TASK
            # in_progress -> completed
            # --------------------------------------
            elif (
                old_status == 'in_progress'
                and new_status == 'completed'
            ):
                if task.start_time is None:
                    task.start_time = timezone.now()

                task.end_time = timezone.now()

            # --------------------------------------
            # UPDATE NORMAL TASK FIELDS
            # --------------------------------------
            serializer = TaskSerializer(
                task,
                data=request.data,
                partial=True
            )

            if not serializer.is_valid():
                return Response(
                    {
                        "status": "0",
                        "errors": serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer.save()

            # Save automatic time fields
            task.save(
                update_fields=[
                    'start_time',
                    'end_time',
                    'updated_at'
                ]
            )

        return Response(
            {
                "status": "1",
                "message": "Task updated successfully"
            },
            status=status.HTTP_200_OK
        )




class TaskRetrieveUpdateDeleteView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

    # -------- RETRIEVE --------
    def get(self, request, pk):
        task = Task.objects.filter(pk=pk).first()
        if not task:
            return Response(
                {"status": "0", "message": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(task)
        return Response(
            {"status": "1", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    # -------- UPDATE (PATCH) --------
    def patch(self, request, pk):
        task = Task.objects.filter(pk=pk).first()
        if not task:
            return Response(
                {"status": "0", "message": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(task, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"status": "0", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        assigned_to = request.data.get("assigned_to")

        with transaction.atomic():
            serializer.save()

            if assigned_to:
                project_member = ProjectMember.objects.filter(pk=assigned_to).first()
                if not project_member:
                    return Response(
                        {"status": "0", "message": "Project member not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # update or create assignment
                TaskAssign.objects.update_or_create(
                    task=task,
                    defaults={
                        "assigned_to": project_member,
                        "assigned_by": request.user
                    }
                )

        return Response(
            {"status": "1", "message": "Task updated successfully"},
            status=status.HTTP_200_OK
        )

    # -------- DELETE --------
    def delete(self, request, pk):
        task = Task.objects.filter(pk=pk).first()
        if not task:
            return Response(
                {"status": "0", "message": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        task.delete()
        return Response(
            {"status": "1", "message": "Task deleted successfully"},
            status=status.HTTP_200_OK
        )


class TaskListByMembers(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

    def get(self, request, member_id, format=None):
        tasks = Task.objects.filter(assignments__assigned_to__member__id=member_id).order_by('-created_at')
        total_tasks = tasks.count()
        not_started_tasks = tasks.filter(status='not_started').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        completed_tasks = tasks.filter(status='completed').count()
        serializer = TaskSerializer(tasks, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "total_tasks": total_tasks,
            "not_started": not_started_tasks,
            "in_progress": in_progress_tasks,
            "completed": completed_tasks,
            "data": serializer.data
        }, status=status.HTTP_200_OK)



class TaskListByProjectMember(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

    def get(self, request, project_member_id):
        project_member = ProjectMember.objects.filter(pk=project_member_id).first()
        if not project_member:
            return Response(
                {"status": "0", "message": "Project member not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        tasks = Task.objects.filter(
            assignments__assigned_to=project_member
        ).select_related(
            'project', 'board'
        ).prefetch_related(
            'assignments'
        ).distinct().order_by('-created_at')

        serializer = TaskSerializer(tasks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


# search views



class TaskSearchByProjectMembersView(APIView):
    permission_classes = [IsAuthenticated]
    

    def get(self, request, project_member_id, format=None):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        task_status = request.query_params.get('status', '').strip()  # ✅ Renamed

        if not start_date_str and not end_date_str and not task_status:
            return Response(
                {"status": "0", "message": "At least one filter ('start_date', 'end_date', or 'status') must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task = Task.objects.filter(
            assignments__assigned_to__id=project_member_id
        ).order_by('-created_at')

        if task_status:
            task = task.filter(status=task_status)
        
        try:
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                task = task.filter(end_date__gte=start_date, end_date__lte=end_date)

            elif start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                task = task.filter(end_date__gte=start_date)

            elif end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                task = task.filter(end_date__lte=end_date)

        except ValueError:
            return Response(
                {"status": "0", "message": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TaskSerializer(task, many=True)

        if not serializer.data:
            return Response(
                {"status": "0", "message": "No tasks found for the given filters."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


class TaskSearchByMembersView(APIView):
    permission_classes = [IsAuthenticated]
    

    def get(self, request, member_id, format=None):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        task_status = request.query_params.get('status', '').strip()  # ✅ Renamed

        if not start_date_str and not end_date_str and not task_status:
            return Response(
                {"status": "0", "message": "At least one filter ('start_date', 'end_date', or 'status') must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task = Task.objects.filter(
            assignments__assigned_to__member__id=member_id
        ).order_by('-created_at')

        if task_status:
            task = task.filter(status=task_status)
        
        try:
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                task = task.filter(end_date__gte=start_date, end_date__lte=end_date)

            elif start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                task = task.filter(end_date__gte=start_date)

            elif end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                task = task.filter(end_date__lte=end_date)

        except ValueError:
            return Response(
                {"status": "0", "message": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TaskSerializer(task, many=True)

        if not serializer.data:
            return Response(
                {"status": "0", "message": "No tasks found for the given filters."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )
    

## DASHBOARD VIEW------#


