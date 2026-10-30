from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..models import (
    MeetingAttendance,
    ProjectManagement,
    ProjectMember,
    ProjectNote,
    Task,
    TaskAssign,
    TaskBoard,
)
from ..serializers import (
    MeetingTaskSerializer,
    ProjectNoteCreateUpdateSerializer,
    ProjectNoteSerializer,
)
from .pagination import ReportPagination

# --------------------------------------------------
# Meeting Minutes Views (Manager / Admin Only)
# --------------------------------------------------
def is_project_manager_or_admin(user, project=None):
    """
    Check if the user is a superuser, staff admin, project owner (PM),
    or has project management permissions.
    Regular staff/developers return False.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if project and getattr(project, 'user_id', None) == user.id:
        return True

    staff_profile = getattr(user, 'staff_profile', None)
    if staff_profile:
        job_detail = getattr(staff_profile, 'job_detail', None)
        if job_detail and job_detail.role:
            role_lower = job_detail.role.lower()
            role_words = set(role_lower.replace('_', ' ').replace('-', ' ').split())
            if any(mgr in role_lower for mgr in ['manager', 'admin', 'lead', 'director', 'head']) or {'pm', 'p.m.'}.intersection(role_words):
                return True

    from accounts.models import ModulePermission
    has_mgr_permission = ModulePermission.objects.filter(
        user=user,
        module_name__in=['project_management', 'project_manager_dashboard', 'project']
    ).exists()
    return has_mgr_permission


class ProjectNoteListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(
            ProjectManagement,
            id=project_id
        )

        if not is_project_manager_or_admin(request.user, project):
            return Response(
                {
                    "status": "0",
                    "message": "Access denied."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        meetings = ProjectNote.objects.filter(
            project=project
        ).select_related(
            'project',
            'created_by'
        ).order_by('-updated_at')

        search = request.query_params.get('search')

        if search:
            search = search.strip()

            meetings = meetings.filter(
                Q(title__icontains=search)
                | Q(content__icontains=search)
            )

        serializer = ProjectNoteSerializer(
            meetings,
            many=True
        )

        return Response(
            {
                "status": "1",
                "message": "success",
                "project_id": project.id,
                "project_name": project.project_name,
                "total_meetings": len(serializer.data),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request, project_id):
        project = get_object_or_404(
            ProjectManagement,
            id=project_id
        )

        if not is_project_manager_or_admin(request.user, project):
            return Response(
                {
                    "status": "0",
                    "message": "Access denied."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProjectNoteCreateUpdateSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                {
                    "status": "0",
                    "message": "Validation failed",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        meeting = serializer.save(
            project=project,
            created_by=request.user
        )

        return Response(
            {
                "status": "1",
                "message": "Meeting created successfully",
                "data": ProjectNoteSerializer(meeting).data
            },
            status=status.HTTP_201_CREATED
        )



class ProjectNoteDetailView(APIView):
    """
    API endpoint for retrieving, updating, and deleting a single project note.
    Only authorized Project Managers and Admins can access.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, note_id):
        project = get_object_or_404(ProjectManagement, id=project_id)
        if not is_project_manager_or_admin(request.user, project):
            return Response(
                {"status": "0", "message": "Access denied: Only project managers and admins can access notes."},
                status=status.HTTP_403_FORBIDDEN
            )

        note = get_object_or_404(ProjectNote.objects.select_related('created_by', 'project'), id=note_id, project=project)
        serializer = ProjectNoteSerializer(note)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, project_id, note_id):
        return self._update(request, project_id, note_id, partial=False)

    def patch(self, request, project_id, note_id):
        return self._update(request, project_id, note_id, partial=True)

    def _update(self, request, project_id, note_id, partial=False):
        project = get_object_or_404(ProjectManagement, id=project_id)
        if not is_project_manager_or_admin(request.user, project):
            return Response(
                {"status": "0", "message": "Access denied: Only project managers and admins can update notes."},
                status=status.HTTP_403_FORBIDDEN
            )

        note = get_object_or_404(ProjectNote.objects.select_related('created_by', 'project'), id=note_id, project=project)
        serializer = ProjectNoteCreateUpdateSerializer(note, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(
                {"status": "0", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()
        response_serializer = ProjectNoteSerializer(note)
        return Response({
            "status": "1",
            "message": "Note updated successfully",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)

    def delete(self, request, project_id, note_id):
        project = get_object_or_404(ProjectManagement, id=project_id)
        if not is_project_manager_or_admin(request.user, project):
            return Response(
                {"status": "0", "message": "Access denied: Only project managers and admins can delete notes."},
                status=status.HTTP_403_FORBIDDEN
            )

        note = get_object_or_404(ProjectNote, id=note_id, project=project)
        note.delete()
        return Response({
            "status": "1",
            "message": "Note deleted successfully"
        }, status=status.HTTP_200_OK)


class MeetingTaskListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = ProjectNote.objects.filter(id=meeting_id).first()

        if not meeting:
            return Response({
                "status": "0",
                "message": "Meeting not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if not is_project_manager_or_admin(request.user, meeting.project):
            return Response({
                "status": "0",
                "message": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        tasks = Task.objects.filter(
            meeting=meeting
        ).select_related(
            "project",
            "board",
            "meeting"
        ).prefetch_related(
            "assignments__assigned_to__member__user",
            "assignments__assigned_by"
        )

        serializer = MeetingTaskSerializer(tasks, many=True)

        return Response({
            "status": "1",
            "message": "Meeting tasks retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request, meeting_id):
        meeting = ProjectNote.objects.filter(id=meeting_id).first()

        if not meeting:
            return Response({
                "status": "0",
                "message": "Meeting not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if not is_project_manager_or_admin(request.user, meeting.project):
            return Response({
                "status": "0",
                "message": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = MeetingTaskSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                "status": "0",
                "message": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data.copy()

        # Get the selected project member
        assigned_to_id = validated_data.pop("assigned_to")

        project_member = ProjectMember.objects.filter(
            id=assigned_to_id,
            project=meeting.project
        ).first()

        if not project_member:
            return Response({
                "status": "0",
                "message": "Assigned member does not belong to this project"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate the board belongs to the meeting's project
        board = validated_data.get("board")

        if board and board.project_id != meeting.project_id:
            return Response({
                "status": "0",
                "message": "Board does not belong to this project"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Create the task
                task = Task.objects.create(
                    **validated_data,
                    project=meeting.project,
                    meeting=meeting
                )

                # Assign the task to the project member
                TaskAssign.objects.create(
                    task=task,
                    assigned_by=request.user,
                    assigned_to=project_member
                )

        except Exception:
            raise

        return Response({
            "status": "1",
            "message": "Meeting task created and assigned successfully",
            "data": {
                **MeetingTaskSerializer(task).data,
                "assigned_to": project_member.id,
                "assigned_to_name": project_member.member.user.get_full_name()
            }
        }, status=status.HTTP_201_CREATED)



class MeetingAttendanceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = ProjectNote.objects.filter(
            id=meeting_id
        ).first()

        if not meeting:
            return Response({
                "status": "0",
                "message": "Meeting not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if not is_project_manager_or_admin(request.user, meeting.project):
            return Response({
                "status": "0",
                "message": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        project_members = ProjectMember.objects.filter(
            project=meeting.project
        ).select_related("member__user", "stack")

        attendance_records = MeetingAttendance.objects.filter(
            meeting=meeting
        ).select_related("project_member")

        attendance_map = {
            record.project_member_id: record.is_present
            for record in attendance_records
        }

        data = []

        for project_member in project_members:
            user = project_member.member.user

            data.append({
                "project_member_id": project_member.id,
                "member_id": project_member.member_id,
                "member_name": user.get_full_name(),
                "email": user.email,
                "is_present": attendance_map.get(
                    project_member.id, False
                ),
                "attendance_marked": (
                    project_member.id in attendance_map
                )
            })

        return Response({
            "status": "1",
            "message": "Meeting attendance retrieved successfully",
            "data": data
        }, status=status.HTTP_200_OK)

    def post(self, request, meeting_id):
        meeting = ProjectNote.objects.filter(
            id=meeting_id
        ).first()

        if not meeting:
            return Response({
                "status": "0",
                "message": "Meeting not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if not is_project_manager_or_admin(request.user, meeting.project):
            return Response({
                "status": "0",
                "message": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        attendees = request.data.get("attendees")

        if not isinstance(attendees, list) or not attendees:
            return Response({
                "status": "0",
                "message": "Provide a non-empty attendees list"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate the full request before saving any attendance.
        validated_attendees = []
        seen_ids = set()

        for item in attendees:
            if not isinstance(item, dict):
                return Response({
                    "status": "0",
                    "message": "Each attendee must be an object"
                }, status=status.HTTP_400_BAD_REQUEST)

            member_id = item.get("project_member_id")
            is_present = item.get("is_present")

            if (
                isinstance(member_id, bool)
                or not isinstance(member_id, int)
                or member_id <= 0
            ):
                return Response({
                    "status": "0",
                    "message": "Each attendee needs a valid project_member_id"
                }, status=status.HTTP_400_BAD_REQUEST)

            if member_id in seen_ids:
                return Response({
                    "status": "0",
                    "message": f"Duplicate project_member_id: {member_id}"
                }, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(is_present, bool):
                return Response({
                    "status": "0",
                    "message": "is_present must be true or false"
                }, status=status.HTTP_400_BAD_REQUEST)

            project_member = ProjectMember.objects.filter(
                id=member_id,
                project=meeting.project
            ).first()

            if not project_member:
                return Response({
                    "status": "0",
                    "message": (
                        f"Project member {member_id} does not belong "
                        "to this meeting's project"
                    )
                }, status=status.HTTP_400_BAD_REQUEST)

            seen_ids.add(member_id)
            validated_attendees.append(
                (project_member, is_present)
            )

        saved_attendance = []

        for project_member, is_present in validated_attendees:
            record, created = MeetingAttendance.objects.update_or_create(
                meeting=meeting,
                project_member=project_member,
                defaults={"is_present": is_present}
            )

            saved_attendance.append({
                "project_member_id": project_member.id,
                "member_name": project_member.member.user.get_full_name(),
                "is_present": record.is_present
            })

        return Response({
            "status": "1",
            "message": "Meeting attendance saved successfully",
            "data": saved_attendance
        }, status=status.HTTP_200_OK)