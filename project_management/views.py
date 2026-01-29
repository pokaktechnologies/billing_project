from django.shortcuts import render,get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from attendance.models import DailyAttendance
from attendance.serializers import DailyAttendanceSessionDetailSerializer
from .serializers import *
from .models import *
from django.db import transaction
from datetime import datetime
from accounts.permissions import HasModulePermission
from django.utils import timezone

from datetime import datetime, timedelta
from math import ceil
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend







#Client contract views
class ClientContractView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request, format=None):
        contracts = ClientContract.objects.all().order_by('-created_at')
        serializer = ClientContractSerializer(contracts, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = ClientContractSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {"status": "1", "message": "Contract created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Contract creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
class ClientContractDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get_contract(self, pk, user):
        try:
            return ClientContract.objects.get(pk=pk)
        except ClientContract.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        contract = self.get_contract(pk, request.user)
        if not contract:
            return Response(
                {"status": "0", "message": "Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClientContractSerializer(contract)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        contract = self.get_contract(pk, request.user)
        if not contract:
            return Response(
                {"status": "0", "message": "Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClientContractSerializer(contract, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Contract updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "message": "Contract update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, format=None):
        contract = self.get_contract(pk, request.user)
        if not contract:
            return Response(
                {"status": "0", "message": "Contract not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        contract.delete()
        return Response(
            {"status": "1", "message": "Contract deleted successfully"},
            status=status.HTTP_200_OK
        )

# Project management views
class project_management(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request, format=None):
        projects = ProjectManagement.objects.all().order_by('-created_at')
        serializer = ProjectManagementSerializer(projects, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = ProjectManagementSerializer(data=request.data)
        members = request.data.get('members')  # Optional

        # Validate members only if provided
        if members:
            member_ids = [item['member'] for item in members]
            if len(member_ids) != len(set(member_ids)):
                return Response(
                    {"status": "0", "message": "Members list contains duplicate members"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if serializer.is_valid():
            # Check if the contract belongs to the user
            contract = ClientContract.objects.filter(pk=request.data.get('contract')).first()
            if not contract:
                return Response(
                    {"status": "0", "message": "Contract not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer.save(user=request.user)

            # Allocate members if any
            if members:
                for member in members:
                    try:
                        member_instance = Member.objects.get(pk=member['member'])
                        stack_instance = Stack.objects.get(pk=member['stack'])
                        ProjectMember.objects.create(
                            project=serializer.instance,
                            member=member_instance,
                            stack=stack_instance
                        )
                    except Member.DoesNotExist:
                        return Response(
                            {"status": "0", "message": f"Member with ID {member['member']} not found"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    except Stack.DoesNotExist:
                        return Response(
                            {"status": "0", "message": f"Stack with ID {member['stack']} not found"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            return Response(
                {"status": "1", "message": "Project created successfully", "project_id": serializer.data['id']},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Project creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )




class project_management_detail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get_project(self, pk, user):
        try:
            project = ProjectManagement.objects.get(pk=pk)
            if not project:
                return None, Response(
                    {"status": "0", "message": "Project not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            return project, None
        except ProjectManagement.DoesNotExist:
            return None, Response(
                {"status": "0", "message": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, pk, format=None):
        project, error_response = self.get_project(pk, request.user)
        if error_response:
            return error_response

        serializer = ProjectManagementDetailsSerializer(project)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        project, error_response = self.get_project(pk, request.user)
        if error_response:
            return error_response

        members = request.data.get('members', [])
        if not isinstance(members, list):
            return Response(
                {"status": "0", "message": "Members should be provided as a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Collect all member and stack IDs
        member_ids = [m.get('member') for m in members]
        stack_ids = [m.get('stack') for m in members]

        member_instances = {m.id: m for m in Member.objects.filter(id__in=member_ids)}
        stack_instances = {s.id: s for s in Stack.objects.filter(id__in=stack_ids)}

        for member in members:
            member_id = member.get('member')
            stack_id = member.get('stack')

            member_instance = member_instances.get(member_id)
            stack_instance = stack_instances.get(stack_id)

            if not member_instance or not stack_instance:
                return Response(
                    {"status": "0", "message": f"Invalid member {member_id} or stack {stack_id}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if the ProjectMember already exists in the project
            project_member = ProjectMember.objects.filter(project=project, member=member_instance).first()

            if project_member:
                # ✅ Member exists in the project: Update the stack
                project_member.stack = stack_instance
                project_member.save()
            else:
                # ✅ Member does not exist: Create a new ProjectMember
                ProjectMember.objects.create(
                    project=project,
                    member=member_instance,
                    stack=stack_instance
                )

        # Serialize the updated project data
        serializer = ProjectManagementSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Project updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "message": "Project update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )





    def delete(self, request, pk, format=None):
        project, error_response = self.get_project(pk, request.user)
        if error_response:
            return error_response

        try:
            project.delete()
            return Response(
                {"status": "1", "message": "Project deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "0", "message": "Project deletion failed", "errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

# Members views

class MembersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request):
        members = Member.objects.all().order_by('-created_at')
        serializer = MemberSerializer(members, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = MemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Member created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class MembersViewDetail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get_member(self, pk):
        try:
            member = Member.objects.get(pk=pk)
            return member, None
        except Member.DoesNotExist:
            return None, Response(
                {"status": "0", "message": "Member not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, pk, format=None):
        member, error_response = self.get_member(pk)
        if error_response:
            return error_response

        serializer = MemberSerializer(member)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        member, error_response = self.get_member(pk)
        if error_response:
            return error_response

        serializer = MemberSerializer(member, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Member updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "message": "Member update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, format=None):
        member, error_response = self.get_member(pk)
        if error_response:
            return error_response

        try:
            member.delete()
            return Response(
                {"status": "1", "message": "Member deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "0", "message": "Member deletion failed", "errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

# Stack views

class StackView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request, format=None):
        stacks = Stack.objects.all().order_by('-created_at')
        serializer = StackSerializer(stacks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = StackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {"status": "1", "message": "Stack created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Stack creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class StackViewDetail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get_stack(self, pk):
        try:
            stack = Stack.objects.get(pk=pk)
            return stack
        except Stack.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        stack = self.get_stack(pk)

        serializer = StackSerializer(stack)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        stack = self.get_stack(pk)
        if not stack:
            return Response(
                {"status": "0", "message": "Stack not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = StackSerializer(stack, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Stack updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "message": "Stack update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, format=None):
        stack = self.get_stack(pk)
        if not stack:
            return Response(
                {"status": "0", "message": "Stack not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            stack.delete()
            return Response(
                {"status": "1", "message": "Stack deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "0", "message": "Stack deletion failed", "errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# Project members views

class ProjectMembersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request, format=None):
        project_members = ProjectMember.objects.all().order_by('-created_at')

        

        if not project_members.exists():
            return Response(
                {"status": "0", "message": "No project members found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProjectMemberSerializer(project_members, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


    def post(self, request, format=None):
        serializer = ProjectMemberSerializer(data=request.data)

        project_id = request.data.get('project')
        stack_id = request.data.get('stack')
        member_id = request.data.get('member')

        if not project_id or not stack_id or not member_id:
            return Response(
                {"status": "0", "message": "Project, Stack, and Member fields are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = ProjectManagement.objects.filter(pk=project_id).first()
        stack = Stack.objects.filter(pk=stack_id).first()
        member = Member.objects.filter(pk=member_id).first()

        missing_entities = []
        if not project:
            missing_entities.append("Project")
        if not stack:
            missing_entities.append("Stack")
        if not member:
            missing_entities.append("Member")

        if missing_entities:
            return Response(
                {"status": "0", "message": f"The following items were not found: {', '.join(missing_entities)}"},
                status=status.HTTP_404_NOT_FOUND
            )

        if ProjectMember.objects.filter(project=project, member=member).exists():
            return Response(
                {"status": "0", "message": "Member already exists in this project"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"status": "1", "message": "Project member created successfully"},
                    status=status.HTTP_201_CREATED
                )

            return Response(
                {"status": "0", "message": "Project member creation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )



class ProjectMembersDetail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get_project_member(self, pk):
        try:
            project_member = ProjectMember.objects.get(pk=pk)
            return project_member
        except ProjectMember.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        project_member = self.get_project_member(pk)
        if not project_member:
            return Response(
                {"status": "0", "message": "Project member not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProjectMemberSerializer(project_member)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        project_member = self.get_project_member(pk)
        if not project_member:
            return Response(
                {"status": "0", "message": "Project member not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        #check member is already in project or not
        if ProjectMember.objects.filter(project=request.data['project'], member=request.data['member']).exists():
            return Response(
                {"status": "0", "message": "Member already exists in this project"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ProjectMemberSerializer(project_member, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Project member updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "message": "Project member update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, format=None):
        project_member = self.get_project_member(pk)
        if not project_member:
            return Response(
                {"status": "0", "message": "Project member not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            project_member.delete()
            return Response(
                {"status": "1", "message": "Project member deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "0", "message": "Project member deletion failed", "errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProjectMembersListByProjectView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request, project_id, format=None):
        project_members = ProjectMember.objects.filter(project__id=project_id).order_by('-created_at')
        serializer = ProjectMemberSerializer(project_members, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

#My Projects
class MyProjectsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    # required_module = 'project_management'

    def get(self, request):
        user = request.user

        projects = ProjectManagement.objects.filter(
            projectmember__member__user=user
        ).select_related('contract').prefetch_related('projectmember_set').distinct()


        serializer = ProjectManagementSerializer(projects, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


class MyProjectDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]

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

        serializer = ProjectManagementSerializer(project)

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )



# Task views


#Create Board
class CreateListBoard(generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'
    queryset = TaskBoard.objects.all().order_by('-updated_at')
    serializer_class = TaskBoardSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

class ListBoardMember(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    # required_module = 'project_management'
    serializer_class = TaskBoardSerializer

    def get_queryset(self):
        return TaskBoard.objects.filter(
            project__projectmember__member__user=self.request.user
        ).select_related('project').distinct().order_by('-updated_at')
    
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

class DistroyUpdateBoard(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'
    queryset = TaskBoard.objects.all()
    serializer_class = TaskBoardSerializer

class CreateStatusColumn(generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'
    serializer_class = StatusColumnWithTasksSerializer

    def get_queryset(self):
        board_id = self.request.query_params.get('board')

        qs = StatusColumns.objects.prefetch_related(
            'task_set'
        ).order_by('id')

        if board_id:
            qs = qs.filter(board_id=board_id)

        return qs


class DistroyUpdateStatusColumn(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'
    queryset = StatusColumns.objects.all()
    serializer_class = StatusColumnWithTasksSerializer


class TaskListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request):
        project = self.request.query_params.get('project')
        if project:
            task = Task.objects.filter(project__id=project).order_by('-created_at')
        else:
            task = Task.objects.all().order_by('-created_at')
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
class MyProjectTaskListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]

    def get(self, request, task_id=None):
        user = request.user
        project_id = request.query_params.get("project")

        tasks = Task.objects.filter(
            assignments__assigned_to__member__user=user
        )

        # optional project filter
        if project_id:
            tasks = tasks.filter(project_id=project_id)

        tasks = tasks.select_related(
            'project', 'board', 'status_column'
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




class TaskRetrieveUpdateDeleteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

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
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request, member_id, format=None):
        tasks = Task.objects.filter(project_member__member__id=member_id).order_by('-created_at')
        serializer = TaskSerializer(tasks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


class TaskListByProjectMember(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

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
            'project', 'board', 'status_column'
        ).prefetch_related(
            'assignments'
        ).distinct().order_by('-created_at')

        serializer = TaskSerializer(tasks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


# search views

class ProjectSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

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

class ProjectMemebrsSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request, project_id,format=None):
        member_name = request.query_params.get('name', '').strip()
        stack = request.query_params.get('stack', '').strip()

        # Ensure at least one filter is provided
        if not member_name and not stack:
            return Response(
                {"status": "0", "message": "At least one filter ('name' or 'stack') must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Base QuerySet: All project members for the logged-in user
        project_members = ProjectMember.objects.filter(project__id=project_id).order_by('-created_at')

        # Filter by member name if provided
        if member_name:
            project_members = project_members.filter(member__name__icontains=member_name)
        
        # Filter by stack if provided
        if stack:
            project_members = project_members.filter(stack__id=stack)

        # Serialize the filtered data
        serializer = ProjectMemberSerializer(project_members, many=True)

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


class MembersSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request):
        member_name = request.query_params.get('name', '').strip()
        role = request.query_params.get('role', '').strip()

        # Ensure at least one filter is provided
        if not member_name and not role:
            return Response(
                {"status": "0", "message": "At least one filter ('name' or 'role') must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Base QuerySet: All members for the logged-in user
        members = Member.objects.all().order_by('-created_at')

        # Filter by member name if provided
        if member_name:
            members = members.filter(name__icontains=member_name)

        # Filter by role if provided
        if role:
            members = members.filter(role=role)

        # Serialize the filtered data
        serializer = MemberSerializer(members, many=True)

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )




class TaskSearchByProjectMembersView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

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
            project_member__id=project_member_id
        ).order_by('-created_at')

        if task_status:
            task = task.filter(status=task_status)
        
        try:
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                task = task.filter(start_date__gte=start_date, end_date__lte=end_date)

            elif start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                task = task.filter(start_date__gte=start_date)

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
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

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
            project_member__member__id=member_id
        ).order_by('-created_at')

        if task_status:
            task = task.filter(status=task_status)
        
        try:
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                task = task.filter(start_date__gte=start_date, end_date__lte=end_date)

            elif start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                task = task.filter(start_date__gte=start_date)

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


class ProjectManagerDashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    # required_module = 'project_management'

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
        assigned_tasks = TaskAssign.objects.select_related("task",
                                                           "assigned_to__member",
                                                           "task__project_member__project"
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

        user_data =  {
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
    

# Pagination class
from rest_framework.pagination import PageNumberPagination
class Pagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


#---------------
# Reporting Module Views
#---------------

class ReportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    # required_module = 'project_management'
    
    def get(self, request, id=None):
        report_type = request.query_params.get('type')  # daily, weekly, monthly
        date_str = request.query_params.get('date')     # YYYY-MM-DD
        week_str = request.query_params.get('week')     # YYYY-MM-DD
        month_str = request.query_params.get('month')   # YYYY-MM

        
        user = request.user

        #  Get member profile
        member = Member.objects.filter(user=user).first()
        if not member:
            return Response(
                {"status": "0", "message": "User is not a project member"},
                status=status.HTTP_403_FORBIDDEN
            )

        #  Get projects where user is a member
        project_ids = ProjectMember.objects.filter(
            member=member
        ).values_list('project_id', flat=True)

        #  IF ID IS PROVIDED → RETRIEVE SINGLE REPORT
        if id is not None:
            try:
                report = Report.objects.select_related(
                    'submitted_by',
                    'submitted_by__staff_profile',
                    'submitted_by__staff_profile__job_detail'
                ).prefetch_related(
                    'tasks',
                    'challenges'
                ).get(
                    id=id,
                    project_id__in=project_ids,
                    submitted_by=user
                )
            except Report.DoesNotExist:
                return Response(
                    {"status": "0", "message": "Report not found or access denied"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = ReportSerializer(report)
            return Response(
                {"status": "1", "message": "success", "data": serializer.data},
                status=status.HTTP_200_OK
            )


        # Fetch reports only for those projects
        reports = Report.objects.filter(
            project_id__in=project_ids,
            submitted_by=user
        )

        #  Filter by report type
        if report_type:
            reports = reports.filter(report_type=report_type)
        
        #  Daily filter
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()

                start_datetime = timezone.make_aware(
                    datetime.combine(date, datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(date, datetime.max.time())
                )

                reports = reports.filter(
                    submitted_at__range=(start_datetime, end_datetime),
                    report_type='daily'
                )

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                    
        #  Weekly filter
        if week_str:
            try:
                week_date = datetime.strptime(week_str, '%Y-%m-%d').date()
                start_week = week_date - timedelta(days=week_date.weekday())
                end_week = start_week + timedelta(days=6)

                start_datetime = timezone.make_aware(
                    datetime.combine(start_week, datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(end_week, datetime.max.time())
                )

                reports = reports.filter(
                    submitted_at__range=(start_datetime, end_datetime),
                    report_type='weekly'
                )

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid week format (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            
        #  Monthly filter
        if month_str:
            try:
                month_date = datetime.strptime(month_str, '%Y-%m')
                start_month = month_date.replace(day=1)
                end_month = (start_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

                start_datetime = timezone.make_aware(
                    datetime.combine(start_month, datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(end_month, datetime.max.time())
                )

                reports = reports.filter(
                    submitted_at__range=(start_datetime, end_datetime),
                    report_type='monthly'
                )

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid month format (YYYY-MM)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        reports = reports.select_related(
            'submitted_by',
            'submitted_by__staff_profile',
            'submitted_by__staff_profile__job_detail'
        ).prefetch_related(
            'tasks',
            'challenges'
        ).order_by('-submitted_at')

        # -----------------
        # Pagination
        # -----------------
        
        paginator = Pagination()
        page = paginator.paginate_queryset(reports, request)

        serializer = ReportSerializer(page, many=True)
        return paginator.get_paginated_response(
            {"status":"1", "message":"success", "data":serializer.data},
        )
    

    def post(self, request):
        user = request.user

        #Get member profile
        member = Member.objects.filter(user=user).first()
        if not member:
            return Response(
                {"status": "0", "message": "User is not a project member"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        #Get project from request
        project_id = request.data.get('project')
        if not project_id:
            return Response(
                {"status": "0", "message": "Project is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        #Check membership for this project
        is_member = ProjectMember.objects.filter(
            project_id=project_id,
            member=member
        ).exists()

        if not is_member:
            return Response(
                {
                    "status": "0",
                    "message": "You are not a member of this project"
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReportSerializer(data=request.data,
                                          context={'request': request})
        if serializer.is_valid():
            serializer.save(submitted_by = user)
            return Response(
                {"status":"1", "message":"Report Created successfully",},
                status = status.HTTP_201_CREATED
            )
        return Response(
            {"status":"0","message":"Report Created Failed","errors":serializer.errors},
            status =status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, id):
        try:
            report = Report.objects.get(
                id=id,
                submitted_by=request.user
            )
        except Report.DoesNotExist:
            return Response(
                {"status": "0", "message": "Report not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReportUpdateSerializer(
            report,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Report updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )



class ReportListManagerView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'
    serializer_class = ReportSerializer
    queryset = Report.objects.all().select_related(
            'submitted_by',
            'submitted_by__staff_profile',
            'submitted_by__staff_profile__job_detail'
        ).prefetch_related(
            'tasks',
            'challenges'
        ).order_by('-submitted_at')
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'project__id', 'submitted_by__id']

class ReportManagerDetailView(generics.RetrieveAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'
    serializer_class = ReportSerializer
    queryset = Report.objects.all().select_related(
            'submitted_by',
            'submitted_by__staff_profile',
            'submitted_by__staff_profile__job_detail'
        ).prefetch_related(
            'tasks',
            'challenges'
        ).order_by('-submitted_at')
    lookup_field = 'id'



class ManagerWeeklyReportSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'project_management'

    def get(self, request):
        project_id = request.query_params.get('project')

        if not project_id:
            return Response(
                {"status": "0", "message": "project is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = get_object_or_404(ProjectManagement, id=project_id)

        #  Project date range
        start_date = project.start_date
        end_date = min(project.end_date, timezone.now().date())

        #  Project members
        members = ProjectMember.objects.filter(
            project=project
        ).select_related('member', 'member__user')

        weeks = []
        current = start_date

        while current <= end_date:
            #  Calculate week range
            week_start = current - timedelta(days=current.weekday())
            week_end = week_start + timedelta(days=6)

            deadline = timezone.make_aware(
                datetime.combine(week_end, datetime.max.time())
            )

            #  Get weekly reports for THIS week
            reports = Report.objects.filter(
                project=project,
                report_type='weekly',
                week_start__lte=week_end,
                week_end__gte=week_start
            )

            report_map = {r.submitted_by_id: r for r in reports}

            submitted = 0
            late = 0
            pending = 0
            employees = []

            for pm in members:
                user = pm.member.user
                report = report_map.get(user.id)

                if report:
                    submitted_on = report.submitted_at.date()

                    #  Late logic
                    if report.submitted_at > deadline:
                        status_text = "Late"
                        late += 1
                    else:
                        status_text = "Submitted"
                        submitted += 1
                else:
                    status_text = "Not Submitted"
                    submitted_on = None
                    pending += 1

                employees.append({
                    "name": f"{user.first_name} {user.last_name}",
                    "role": pm.member.role,
                    "submitted_on": submitted_on,
                    "status": status_text,
                    "report_id": report.id if report else None
                })

            weeks.append({
                "week_start": week_start,
                "week": f"{week_start.strftime('%d %b')} – {week_end.strftime('%d %b %Y')}",
                "submitted": submitted,
                "late": late,
                "pending": pending,
                "employees": employees
            })

            current = week_end + timedelta(days=1)

        #  Latest week first
        weeks = sorted(weeks, key=lambda x: x["week_start"], reverse=True)
        for w in weeks:
            w.pop("week_start")

        # -----------------
        # Pagination
        # -----------------
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))  # default 4 weeks

        total_items = len(weeks)
        total_pages = ceil(total_items / page_size)

        start = (page - 1) * page_size
        end = start + page_size

        paginated_weeks = weeks[start:end]

        return Response(
            {
                "status": "1",
                "message": "success",
                "pagination": {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "page_size": page_size,
                    "next_page": page + 1 if page < total_pages else None,
                    "previous_page": page - 1 if page > 1 else None
                },
                "weeks": paginated_weeks
            },
            status=status.HTTP_200_OK
        )

