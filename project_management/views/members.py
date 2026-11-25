from datetime import datetime
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import CustomUser, Department, StaffProfile
from activity_logs.base_view import BaseAPIView
from ..models import Member, Stack, ProjectMember, ProjectManagement
from ..serializers import MemberSerializer, StackSerializer, ProjectMemberSerializer
from .pagination import ReportPagination

class MembersView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    

    def get(self, request):
        status_filter = request.query_params.get('status')
        members = Member.objects.all().order_by('-created_at')
        if status_filter:
            members = members.filter(status=status_filter)
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
            # Soft-deactivate to prevent cascading deletion of tasks, project memberships, and reports
            member.status = 'inactive'
            member.is_active = False
            member.save(update_fields=['status', 'is_active'])

            ProjectMember.objects.filter(member=member, is_active=True).update(
                status='inactive',
                is_active=False
            )

            return Response(
                {"status": "1", "message": "Member deactivated successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "0", "message": "Member deactivation failed", "errors": str(e)},
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
        project_id = request.data.get('project')
        member_id = request.data.get('member')
        user_id = request.data.get('user') or request.data.get('user_id')
        staff_id = request.data.get('staff') or request.data.get('staff_id')
        dept_id = request.data.get('department') or request.data.get('department_id')
        stack_id = request.data.get('stack') or request.data.get('stack_id')

        if not project_id:
            return Response(
                data={"status": "0", "message": "Project field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = ProjectManagement.objects.filter(pk=project_id).first()
        if not project:
            return Response(
                data={"status": "0", "message": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Resolve member
        member = None
        if member_id:
            member = Member.objects.filter(pk=member_id).first()
            if not member:
                return Response(
                    data={"status": "0", "message": f"Member with ID {member_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif user_id:
            user = CustomUser.objects.filter(pk=user_id).first()
            if not user:
                return Response(
                    data={"status": "0", "message": f"User with ID {user_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            member, _ = Member.objects.get_or_create(
                user=user,
                defaults={'status': 'active', 'is_active': True}
            )
        elif staff_id:
            staff = StaffProfile.objects.select_related('user').filter(pk=staff_id).first()
            if not staff:
                return Response(
                    data={"status": "0", "message": f"Staff with ID {staff_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            member, _ = Member.objects.get_or_create(
                user=staff.user,
                defaults={'status': 'active', 'is_active': True}
            )
        else:
            return Response(
                data={"status": "0", "message": "Member, user, or staff is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If member was inactive, reactivate
        if not member.is_active or member.status != 'active':
            member.status = 'active'
            member.is_active = True
            member.save(update_fields=['status', 'is_active'])

        # Resolve department & stack
        department = None
        if dept_id:
            department = Department.objects.filter(pk=dept_id).first()
            if not department:
                return Response(
                    data={"status": "0", "message": f"Department with ID {dept_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        stack = None
        if stack_id:
            stack = Stack.objects.filter(pk=stack_id).first()
            if not stack:
                return Response(
                    data={"status": "0", "message": f"Stack with ID {stack_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Auto-resolve department from staff profile if neither department nor stack is provided
        if not department and not stack:
            staff_prof = getattr(member.user, 'staff_profile', None)
            if staff_prof and getattr(staff_prof, 'job_detail', None) and staff_prof.job_detail.department:
                department = staff_prof.job_detail.department

        # Auto-match or create stack by department name for legacy compatibility
        if not stack and department:
            stack, _ = Stack.objects.get_or_create(
                name=department.name,
                defaults={'user': member.user}
            )

        with transaction.atomic():
            project_member = ProjectMember.objects.filter(project=project, member=member).first()
            if project_member:
                if project_member.is_active and project_member.status == 'active':
                    return Response(
                        data={"status": "0", "message": "Member already exists in this project"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Reactivate if it was soft-deleted/inactive
                project_member.status = 'active'
                project_member.is_active = True
                if department:
                    project_member.department = department
                if stack:
                    project_member.stack = stack
                project_member.save(update_fields=['status', 'is_active', 'department', 'stack'])
            else:
                project_member = ProjectMember.objects.create(
                    project=project,
                    member=member,
                    department=department,
                    stack=stack,
                    status='active',
                    is_active=True
                )

            serializer = ProjectMemberSerializer(project_member)
            return Response(
                data={"status": "1", "message": "Project member created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
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
        target_project = request.data.get('project', project_member.project_id)
        target_member = request.data.get('member', project_member.member_id)
        if ProjectMember.objects.filter(project=target_project, member=target_member).exclude(pk=pk).exists():
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
            # Soft-deactivate to prevent cascading deletion of task assignments
            project_member.status = 'inactive'
            project_member.is_active = False
            project_member.save(update_fields=['status', 'is_active'])
            return Response(
                {"status": "1", "message": "Project member deactivated successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"status": "0", "message": "Project member deactivation failed", "errors": str(e)},
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


class DepartmentStaffListView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        department_filter = request.query_params.get('department')
        search_query = request.query_params.get('search', '').strip()

        departments = Department.objects.all().order_by('name')
        departments_data = [
            {'id': d.id, 'name': d.name}
            for d in departments
        ]

        staff_qs = StaffProfile.objects.select_related(
            'user', 'job_detail', 'job_detail__department'
        ).filter(user__is_active=True)

        if department_filter:
            staff_qs = staff_qs.filter(job_detail__department_id=department_filter)

        if search_query:
            staff_qs = staff_qs.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(job_detail__role__icontains=search_query)
            )

        existing_members = {
            m.user_id: m.id
            for m in Member.objects.all()
        }

        staff_data = []
        for staff in staff_qs:
            user = staff.user
            job_detail = getattr(staff, 'job_detail', None)
            dept = getattr(job_detail, 'department', None) if job_detail else None
            staff_data.append({
                'user_id': user.id,
                'staff_id': staff.id,
                'name': f"{user.first_name} {user.last_name}".strip(),
                'email': user.email,
                'role': getattr(job_detail, 'role', '') if job_detail else '',
                'department_id': dept.id if dept else None,
                'department_name': dept.name if dept else None,
                'member_id': existing_members.get(user.id),
            })

        return Response({
            "status": "1",
            "message": "success",
            "departments": departments_data,
            "staff": staff_data,
        }, status=status.HTTP_200_OK)





