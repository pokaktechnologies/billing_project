from datetime import datetime
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_logs.base_view import BaseAPIView
from ..models import (
    ClientContract,
    Member,
    ProjectManagement,
    ProjectMember,
    Stack,
    Task,
    TaskAssign,
    TaskBoard,
)
from ..serializers import (
    ProjectManagementDetailsSerializer,
    ProjectManagementSerializer,
    ProjectTimelineSerializer,
)
from .pagination import ReportPagination


def get_project_progress_data(project):
    task_counts = Task.objects.filter(project=project).aggregate(
        total_tasks=Count('id'),
        not_started=Count('id', filter=Q(status='not_started')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        completed=Count('id', filter=Q(status='completed')),
    )

    total_tasks = task_counts["total_tasks"] or 0
    not_started = task_counts["not_started"] or 0
    in_progress = task_counts["in_progress"] or 0
    completed = task_counts["completed"] or 0

    total_tasks_point = total_tasks * 2

    total_point = (
        not_started * 0 +
        in_progress * 1 +
        completed * 2
    )

    progression_percentage = (
        (total_point / total_tasks_point) * 100
        if total_tasks_point > 0 else 0.0
    )

    return {
        "total_tasks": total_tasks,
        "not_started_tasks": not_started,
        "in_progress_tasks": in_progress,
        "completed_tasks": completed,
        "progression_percentage": round(progression_percentage, 2),
    }


class project_management(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        projects = ProjectManagement.objects.all()

        project_type = request.query_params.get('project_type')

        if project_type:
            valid_types = ['dev', 'dm', 'testing']

            if project_type not in valid_types:
                return Response(
                    {
                        "status": "0",
                        "message": "Invalid project type"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            projects = projects.filter(project_type=project_type)

        projects = projects.order_by('-created_at')

        serializer = ProjectManagementSerializer(
            projects,
            many=True
        )

        return Response(
            {
                "status": "1",
                "message": "success",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = ProjectManagementSerializer(data=request.data)

        members = request.data.get('members', [])
        boards = request.data.get('boards', [])

        project_type = request.data.get('project_type', 'dev')

        # Validate project type
        valid_types = ['dev', 'dm', 'testing']

        if project_type not in valid_types:
            return Response(
                {
                    "status": "0",
                    "message": "Invalid project type"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate members
        if not isinstance(members, list):
            return Response(
                {
                    "status": "0",
                    "message": "Members should be provided as a list"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        member_ids = []

        for item in members:
            if not isinstance(item, dict):
                return Response(
                    {
                        "status": "0",
                        "message": "Each member must be an object"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not item.get('member') or not item.get('stack'):
                return Response(
                    {
                        "status": "0",
                        "message": "Member and stack are required"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            member_ids.append(item['member'])

        if len(member_ids) != len(set(member_ids)):
            return Response(
                {
                    "status": "0",
                    "message": "Members list contains duplicate members"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate boards
        if not isinstance(boards, list):
            return Response(
                {
                    "status": "0",
                    "message": "Boards should be provided as a list"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate project data
        if not serializer.is_valid():
            return Response(
                {
                    "status": "0",
                    "message": "Project creation failed",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Contract is mandatory only for developer projects
        contract = None
        contract_id = request.data.get('contract')

        if contract_id:
            contract = ClientContract.objects.filter(
                pk=contract_id
            ).first()

            if not contract:
                return Response(
                    {
                        "status": "0",
                        "message": "Contract not found"
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

        if project_type == 'dev' and not contract:
            return Response(
                {
                    "status": "0",
                    "message": "Contract is required for developer projects"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():

                # Create project
                project = serializer.save(
                    user=request.user,
                    project_type=project_type
                )

                # Allocate members
                for member in members:
                    try:
                        member_instance = Member.objects.get(
                            pk=member['member']
                        )

                        stack_instance = Stack.objects.get(
                            pk=member['stack']
                        )

                    except Member.DoesNotExist:
                        raise ValueError(
                            f"Member with ID {member['member']} not found"
                        )

                    except Stack.DoesNotExist:
                        raise ValueError(
                            f"Stack with ID {member['stack']} not found"
                        )

                    ProjectMember.objects.create(
                        project=project,
                        member=member_instance,
                        stack=stack_instance
                    )

                # Create task boards
                for board in boards:
                    if not isinstance(board, dict):
                        raise ValueError(
                            "Each board must be an object"
                        )

                    name = board.get('name')

                    if not name:
                        raise ValueError(
                            "TaskBoard name is required"
                        )

                    TaskBoard.objects.create(
                        project=project,
                        name=name,
                        start_date=board.get('start_date') or None,
                        end_date=board.get('end_date') or None
                    )

        except ValueError as e:
            return Response(
                {
                    "status": "0",
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response(
                {
                    "status": "0",
                    "message": "Project creation failed",
                    "errors": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "status": "1",
                "message": "Project created successfully",
                "project_id": project.id,
                "project_type": project.project_type
            },
            status=status.HTTP_201_CREATED
        )


class project_management_detail(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_project(self, pk, user):
        try:
            return ProjectManagement.objects.get(pk=pk), None

        except ProjectManagement.DoesNotExist:
            return None, Response(
                {
                    "status": "0",
                    "message": "Project not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, pk, format=None):
        project, error_response = self.get_project(
            pk,
            request.user
        )

        if error_response:
            return error_response

        serializer = ProjectManagementDetailsSerializer(project)

        return Response(
            {
                "status": "1",
                "message": "success",
                "data": [serializer.data]
            },
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        project, error_response = self.get_project(
            pk,
            request.user
        )

        if error_response:
            return error_response

        # Only update member allocations when members is provided
        members = request.data.get('members', None)

        if members is not None and not isinstance(members, list):
            return Response(
                {
                    "status": "0",
                    "message": "Members should be provided as a list"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate member and stack IDs before updating anything
        member_instances = {}
        stack_instances = {}

        if members is not None:
            member_ids = []
            stack_ids = []

            for item in members:
                if not isinstance(item, dict):
                    return Response(
                        {
                            "status": "0",
                            "message": "Each member must be an object"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if not item.get('member') or not item.get('stack'):
                    return Response(
                        {
                            "status": "0",
                            "message": "Member and stack are required"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                member_ids.append(item['member'])
                stack_ids.append(item['stack'])

            if len(member_ids) != len(set(member_ids)):
                return Response(
                    {
                        "status": "0",
                        "message": "Members list contains duplicate members"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            member_instances = {
                obj.id: obj
                for obj in Member.objects.filter(id__in=member_ids)
            }

            stack_instances = {
                obj.id: obj
                for obj in Stack.objects.filter(id__in=stack_ids)
            }

            for item in members:
                member_id = item['member']
                stack_id = item['stack']

                if (
                    member_id not in member_instances
                    or stack_id not in stack_instances
                ):
                    return Response(
                        {
                            "status": "0",
                            "message": (
                                f"Invalid member {member_id} "
                                f"or stack {stack_id}"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Validate project fields
        serializer = ProjectManagementSerializer(
            project,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            return Response(
                {
                    "status": "0",
                    "message": "Project update failed",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine the final project type
        project_type = serializer.validated_data.get(
            'project_type',
            project.project_type
        )

        valid_types = ['dev', 'dm', 'testing']

        if project_type not in valid_types:
            return Response(
                {
                    "status": "0",
                    "message": "Invalid project type"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Preserve the existing contract unless a new value is supplied
        contract = serializer.validated_data.get(
            'contract',
            project.contract
        )

        if project_type == 'dev' and not contract:
            return Response(
                {
                    "status": "0",
                    "message": "Contract is required for developer projects"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():

                serializer.save()

                # Update or add members only if provided
                if members is not None:
                    for item in members:
                        member_instance = member_instances[item['member']]
                        stack_instance = stack_instances[item['stack']]

                        project_member = ProjectMember.objects.filter(
                            project=project,
                            member=member_instance
                        ).first()

                        if project_member:
                            project_member.stack = stack_instance
                            project_member.save(
                                update_fields=['stack']
                            )
                        else:
                            ProjectMember.objects.create(
                                project=project,
                                member=member_instance,
                                stack=stack_instance
                            )

        except Exception as e:
            return Response(
                {
                    "status": "0",
                    "message": "Project update failed",
                    "errors": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "status": "1",
                "message": "Project updated successfully"
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, pk, format=None):
        project, error_response = self.get_project(
            pk,
            request.user
        )

        if error_response:
            return error_response

        try:
            project.delete()

            return Response(
                {
                    "status": "1",
                    "message": "Project deleted successfully"
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {
                    "status": "0",
                    "message": "Project deletion failed",
                    "errors": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class ProjectProgressionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(ProjectManagement, id=project_id)

        return Response(
            {
                "status": "1",
                "message": "success",
                "data": get_project_progress_data(project)
            },
            status=status.HTTP_200_OK
        )


class MyProjectsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        projects = ProjectManagement.objects.filter(
            projectmember__member__user=user
        ).select_related('contract').prefetch_related('projectmember_set').distinct()

        serializer = ProjectManagementSerializer(projects, many=True)
        project_data = serializer.data

        # map project_id -> project_object
        project_map = {project.id: project for project in projects}

        for project in project_data:
            project_obj = project_map.get(project["id"])
            project["progress_data"] = get_project_progress_data(project_obj)

        return Response(
            {"status": "1", "message": "success", "data": project_data},
            status=status.HTTP_200_OK
        )


class MyProjectDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        user = request.user

        project = ProjectManagement.objects.filter(
            id=project_id,
            projectmember__member__user=user
        ).select_related('contract').first()

        if not project:
            return Response(
                {"status": "0", "message": "Project not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )

        data = ProjectManagementSerializer(project).data
        data["progress_data"] = get_project_progress_data(project)

        return Response(
            {"status": "1", "message": "success", "data": data},
            status=status.HTTP_200_OK
        )


class ProjectReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = ProjectManagement.objects.select_related('contract').prefetch_related('task_set').order_by('-created_at')

        # FILTER PARAMETERS
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        status = request.query_params.get('status')
        search = request.query_params.get('search')

        # DATE FILTER (ACTIVE PROJECTS)
        if from_date and to_date:
            try:
                from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

                projects = projects.filter(
                    start_date__lte=to_date,
                    end_date__gte=from_date
                )

            except ValueError:
                return Response({
                    "Status": "0",
                    "Message": "Invalid date format. Use YYYY-MM-DD"
                })

        # STATUS FILTER
        if status:
            projects = projects.filter(status=status)

        # SEARCH FILTER
        if search:
            projects = projects.filter(
                project_name__icontains=search
            )

        # PAGINATION
        paginator = ReportPagination()
        paginated_qs = paginator.paginate_queryset(projects, request)

        if paginated_qs is not None:
            serializer = ProjectManagementSerializer(paginated_qs, many=True)
            data = serializer.data

            for i, project in enumerate(paginated_qs):
                data[i]["progress"] = get_project_progress_data(project)

            return paginator.get_paginated_response({
                "Status": "1",
                "Message": "Success",
                "Data": data
            })

        # If no pagination
        serializer = ProjectManagementSerializer(projects, many=True)
        data = serializer.data

        for i, project in enumerate(projects):
            data[i]["progress"] = get_project_progress_data(project)

        return Response({
            "Status": "1",
            "Message": "Success",
            "Data": data
        })


class ProjectTimelineReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        search = request.query_params.get('search')

        project = ProjectManagement.objects.filter(id=id).first()

        if not project:
            return Response(
                {"status": "0", "message": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        project_members = ProjectMember.objects.filter(project_id=id) \
            .select_related('member__user', 'project', 'stack')

        if search:
            project_members = project_members.filter(
                Q(member__user__first_name__icontains=search) |
                Q(member__user__last_name__icontains=search) |
                Q(member__user__email__icontains=search)
            )

        task_data = TaskAssign.objects.filter(
            assigned_to__project_id=id
        ).values('assigned_to').annotate(
            total_tasks=Count('id'),
            completed_tasks=Count('id', filter=Q(task__status='completed')),
            pending_tasks=Count('id', filter=~Q(task__status='completed')),
            easy_tasks=Count('id', filter=Q(task__difficulty='easy')),
            medium_tasks=Count('id', filter=Q(task__difficulty='medium')),
            hard_tasks=Count('id', filter=Q(task__difficulty='hard')),
        )

        task_map = {item['assigned_to']: item for item in task_data}

        pagination = ReportPagination()
        paginated_qs = pagination.paginate_queryset(project_members, request)
        if paginated_qs is not None:
            serializer = ProjectTimelineSerializer(
                paginated_qs,
                many=True,
                context={'task_map': task_map}
            )
            return pagination.get_paginated_response(serializer.data)

        serializer = ProjectTimelineSerializer(
            project_members,
            many=True,
            context={'task_map': task_map}
        )

        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class ProjectSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_name = request.query_params.get('name', '').strip()
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        # Ensure at least one filter is provided
        if not project_name and not start_date_str and not end_date_str:
            return Response(
                {"status": "0", "message": "At least one filter ('name', 'start_date', or 'end_date') must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Base QuerySet: All projects for the logged-in user
        projects = ProjectManagement.objects.all().order_by('-created_at')

        # Filter by project name if provided
        if project_name:
            projects = projects.filter(project_name__icontains=project_name)

        try:
            # Filter by overlapping date range if both dates are provided
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

                projects = projects.filter(
                    start_date__gte=start_date,   # Starts after or on the provided start date
                    end_date__lte=end_date        # Ends before or on the provided end date
                )

            #  Filter by start_date only
            elif start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                projects = projects.filter(start_date__gte=start_date)

            #  Filter by end_date only
            elif end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                projects = projects.filter(end_date__lte=end_date)

        except ValueError:
            return Response(
                {"status": "0", "message": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        #  Serialize the filtered data
        serializer = ProjectManagementSerializer(projects, many=True)

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
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
