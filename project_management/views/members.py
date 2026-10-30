from datetime import datetime
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_logs.base_view import BaseAPIView
from ..models import Member, Stack, ProjectMember, ProjectManagement
from ..serializers import MemberSerializer, StackSerializer, ProjectMemberSerializer
from .pagination import ReportPagination

class MembersView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

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

class MembersViewDetail(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

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

class StackView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

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

class StackViewDetail(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

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

class ProjectMembersView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

    def get(self, request):
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



class ProjectMembersDetail(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

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
    permission_classes = [IsAuthenticated]
    

    def get(self, request, project_id):
        project_members = ProjectMember.objects.filter(project__id=project_id).order_by('-created_at')
        serializer = ProjectMemberSerializer(project_members, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )
class ProjectMembersViewListByProjectView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        user = request.user
        if not ProjectMember.objects.filter(project__id=project_id, member__user=user).exists():
            return Response(
                {"status": "0", "message": "Access denied to this project's members"},
                status=status.HTTP_403_FORBIDDEN
            )
        project_members = ProjectMember.objects.filter(project__id=project_id).order_by('-created_at')
        serializer = ProjectMemberSerializer(project_members, many=True)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )



class ProjectMembersSearchView(APIView):
    permission_classes = [IsAuthenticated]
    

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
            project_members = project_members.filter(member__user__first_name__icontains=member_name)
        
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
    permission_classes = [IsAuthenticated]
    

    def get(self, request):
        search = request.query_params.get('search', '').strip()

        # Ensure search parameter is provided
        if not search:
            return Response(
                {"status": "0", "message": "Search parameter must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Base QuerySet: All members for the logged-in user
        members = Member.objects.filter(
            Q(user__first_name__icontains=search) | Q(user__staff_profile__job_detail__role__icontains=search)
        ).order_by('-created_at')

        # Serialize the filtered data
        serializer = MemberSerializer(members, many=True)

        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )




