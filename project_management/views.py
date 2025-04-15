from django.shortcuts import render,get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import *
from .models import *
from django.db import transaction


class project_management(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        projects = ProjectManagement.objects.filter(user=request.user).order_by('-created_at')
        serializer = ProjectManagementSerializer(projects, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = ProjectManagementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {"status": "1", "message": "Project created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Project creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class project_management_detail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_project(self, pk, user):
        try:
            project = ProjectManagement.objects.get(pk=pk, user=user)
            if project.user != user:
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

        serializer = ProjectManagementSerializer(project)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        project, error_response = self.get_project(pk, request.user)
        if error_response:
            return error_response

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


class MembersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        members = Member.objects.filter(user=request.user).order_by('-created_at')
        serializer = MemberSerializer(members, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )
    
    def post(self, request, format=None):
        serializer = MemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {"status": "1", "message": "Member created successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": "0", "message": "Member creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class MembersViewDetail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_member(self, pk, user):
        try:
            member = Member.objects.get(pk=pk, user=user)
            if member.user != user:
                return None, Response(
                    {"status": "0", "message": "Member not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            return member, None
        except Member.DoesNotExist:
            return None, Response(
                {"status": "0", "message": "Member not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, pk, format=None):
        member, error_response = self.get_member(pk, request.user)
        if error_response:
            return error_response

        serializer = MemberSerializer(member)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        member, error_response = self.get_member(pk, request.user)
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
        member, error_response = self.get_member(pk, request.user)
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


class StackView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        stacks = Stack.objects.filter(user=request.user).order_by('-created_at')
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
    permission_classes = [IsAuthenticated]

    def get_stack(self, pk):
        try:
            stack = Stack.objects.get(pk=pk, user=self.request.user)
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


class ProjectMembersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        project_members = ProjectMember.objects.filter(project__user=request.user).order_by('-created_at')

        

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

        # Check project belongs to user or not
        project = ProjectManagement.objects.filter(pk=request.data.get('project'), user=request.user).first()
        # check stack is belongs to user or not
        stack = Stack.objects.filter(pk=request.data.get('stack'), user=request.user).first()
        # check member is belongs to user or not
        member = Member.objects.filter(pk=request.data.get('member'), user=request.user).first()

        missing_entities = []
        if not project:
            missing_entities.append("Project")
        if not stack:
            missing_entities.append("Stack")
        if not member:
            missing_entities.append("Member")

        if missing_entities:
            return Response(
            {"status": "0", "message": f"{', '.join(missing_entities)} not found"},
            status=status.HTTP_404_NOT_FOUND
            )

        # Check if member is already in the project
        if ProjectMember.objects.filter(project=request.data['project'], member=request.data['member']).exists():
            return Response(
                {"status": "0", "message": "Member already exists in this project"},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        # Start a transaction block
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
    permission_classes = [IsAuthenticated]

    def get_project_member(self, pk):
        try:
            project_member = ProjectMember.objects.get(pk=pk, project__user=self.request.user)
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
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, format=None):
        project_members = ProjectMember.objects.filter(project__id=project_id, project__user=request.user).order_by('-created_at')
        serializer = ProjectMemberSerializer(project_members, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

class TaskView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        tasks = Task.objects.filter(project_member__project__user=request.user).order_by('-created_at')
       
        serializer = TaskSerializer(tasks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def post(self, request, format=None):
        serializer = TaskSerializer(data=request.data)

        # Check if project member belongs to user or not
        project_member = ProjectMember.objects.filter(pk=request.data.get('project_member'), project__user=request.user).first()
        if not project_member:
            return Response(
                {"status": "0", "message": "Project member not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Start a transaction block
        with transaction.atomic():
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"status": "1", "message": "Task created successfully"},
                    status=status.HTTP_201_CREATED
                )

        return Response(
            {"status": "0", "message": "Task creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class TaskDetail(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_task(self, pk):
        try:
            task = Task.objects.get(pk=pk, project_member__project__user=self.request.user)
            return task
        except Task.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        task = self.get_task(pk)
        if not task:
            return Response(
                {"status": "0", "message": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(task)
        return Response(
            {"status": "1", "message": "success", "data": [serializer.data]},
            status=status.HTTP_200_OK
        )

    def patch(self, request, pk, format=None):
        task = self.get_task(pk)
        if not task:
            return Response(
                {"status": "0", "message": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "1", "message": "Task updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": "0", "message": "Task update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, format=None):
        task = self.get_task(pk)
        if not task:
            return Response(
                {"status": "0", "message": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            task.delete()
            return Response(
                {"status": "1", "message": "Task deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "0", "message": "Task deletion failed", "errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class TaskListByMembers(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, member_id, format=None):
        tasks = Task.objects.filter(project_member__member__id=member_id, project_member__project__user=request.user).order_by('-created_at')
        serializer = TaskSerializer(tasks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


class TaskListByProjectMember(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_member_id, format=None):
        tasks = Task.objects.filter(project_member__id=project_member_id, project_member__project__user=request.user).order_by('-created_at')
        serializer = TaskSerializer(tasks, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )



