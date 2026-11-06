
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..models.testing import BugReport, BugStatusHistory
from ..models import ProjectManagement, ProjectMember
from ..serializers.testing import BugReportSerializer


class BugSheetListCreateAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # GET: List bugs for a project.
    def get(self, request):

        project_id = request.query_params.get('project')

        if not project_id:
            return Response(
                {
                    "status": "0",
                    "message": "Project ID is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        project = ProjectManagement.objects.filter(
            id=project_id
        ).first()

        if not project:
            return Response(
                {
                    "status": "0",
                    "message": "Project not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        is_project_member = ProjectMember.objects.filter(
            project=project,
            member__user=request.user
        ).exists()

        is_reporter = BugReport.objects.filter(
            project=project,
            reported_by=request.user
        ).exists()

        if not (
            is_project_member
            or is_reporter
            or request.user.is_staff
        ):
            return Response(
                {
                    "status": "0",
                    "message": "You do not have access to this project"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        bugs = BugReport.objects.filter(
            project=project
        )

        module = request.query_params.get('module')
        severity = request.query_params.get('severity')
        bug_status = request.query_params.get('status')

        if module:
            bugs = bugs.filter(module__iexact=module)

        if severity:
            bugs = bugs.filter(severity=severity)

        if bug_status:
            bugs = bugs.filter(status=bug_status)

        bugs = bugs.select_related(
            'project',
            'reported_by',
            'fixed_by'
        ).order_by('-created_at')

        serializer = BugReportSerializer(
            bugs,
            many=True,
            context={'request': request}
        )

        return Response(
            {
                "status": "1",
                "message": "success",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    # POST: Create a new bug.
    def post(self, request):

        serializer = BugReportSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                {
                    "status": "0",
                    "message": "Bug creation failed",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        project = serializer.validated_data['project']

        is_project_member = ProjectMember.objects.filter(
            project=project,
            member__user=request.user
        ).exists()

        # Temporary rule:
        # Project members and staff can report bugs.
        # Replace this with your actual tester-role permission
        # once the role structure is confirmed.
        if not is_project_member and not request.user.is_staff:
            return Response(
                {
                    "status": "0",
                    "message": "You are not authorized to report bugs for this project"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            with transaction.atomic():

                bug = serializer.save(
                    reported_by=request.user,
                    status='open'
                )

                BugStatusHistory.objects.create(
                    bug=bug,
                    old_status='',
                    new_status='open',
                    changed_by=request.user,
                    comment='Bug reported'
                )

            return Response(
                {
                    "status": "1",
                    "message": "Bug reported successfully",
                    "data": BugReportSerializer(
                        bug,
                        context={'request': request}
                    ).data
                },
                status=status.HTTP_201_CREATED
            )

        except Exception:
            return Response(
                {
                    "status": "0",
                    "message": "Unable to create bug report"
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class BugReportDetailAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_bug(self, bug_id, user):

        bug = BugReport.objects.filter(
            id=bug_id
        ).select_related(
            'project',
            'reported_by',
            'fixed_by'
        ).first()

        if not bug:
            return None

        is_project_member = ProjectMember.objects.filter(
            project=bug.project,
            member__user=user
        ).exists()

        if (
            not is_project_member
            and bug.reported_by_id != user.id
            and not user.is_staff
        ):
            return None

        return bug

    def get(self, request, bug_id):

        bug = self.get_bug(bug_id, request.user)

        if not bug:
            return Response(
                {
                    "status": "0",
                    "message": "Bug not found or access denied"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BugReportSerializer(
            bug,
            context={'request': request}
        )

        history = bug.status_history.select_related(
            'changed_by'
        ).order_by('-changed_at')

        history_data = [
            {
                "old_status": item.old_status,
                "new_status": item.new_status,
                "changed_by": item.changed_by.first_name,
                "comment": item.comment,
                "changed_at": item.changed_at,
            }
            for item in history
        ]

        data = serializer.data
        data['status_history'] = history_data

        return Response(
            {
                "status": "1",
                "message": "success",
                "data": data
            },
            status=status.HTTP_200_OK
        )


class BugStatusUpdateAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, bug_id):

        try:
            with transaction.atomic():

                bug = BugReport.objects.select_for_update().filter(
                    id=bug_id
                ).select_related(
                    'project',
                    'reported_by',
                    'fixed_by'
                ).first()

                if not bug:
                    return Response(
                        {
                            "status": "0",
                            "message": "Bug not found"
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )

                user = request.user

                is_project_member = ProjectMember.objects.filter(
                    project=bug.project,
                    member__user=user
                ).exists()

                is_reporter = bug.reported_by_id == user.id
                is_admin = user.is_staff

                if not (
                    is_project_member
                    or is_reporter
                    or is_admin
                ):
                    return Response(
                        {
                            "status": "0",
                            "message": "You do not have permission to update this bug"
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

                new_status = request.data.get('status')
                comment = request.data.get('comment', '')

                allowed_statuses = dict(BugReport.STATUS_CHOICES)

                if new_status not in allowed_statuses:
                    return Response(
                        {
                            "status": "0",
                            "message": "Invalid bug status",
                            "allowed_statuses": list(allowed_statuses.keys())
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                old_status = bug.status

                if old_status == new_status:
                    return Response(
                        {
                            "status": "0",
                            "message": "Bug already has this status"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Project members can mark bugs Fixed or Pending.
                developer_statuses = ['fixed', 'pending']

                # Original reporter can verify or reopen bugs.
                tester_statuses = [
                    'closed',
                    'reopen',
                    'open',
                    'suggestion',
                    'not_a_bug'
                ]

                if is_admin:
                    pass

                elif is_project_member and new_status in developer_statuses:
                    pass

                elif is_reporter and new_status in tester_statuses:
                    pass

                else:
                    return Response(
                        {
                            "status": "0",
                            "message": "You are not allowed to set this status"
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Only Fixed bugs can be closed.
                if new_status == 'closed' and old_status != 'fixed':
                    return Response(
                        {
                            "status": "0",
                            "message": "Only a fixed bug can be closed"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Only Fixed or Closed bugs can be reopened.
                if new_status == 'reopen' and old_status not in [
                    'fixed',
                    'closed'
                ]:
                    return Response(
                        {
                            "status": "0",
                            "message": "Only fixed or closed bugs can be reopened"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update bug status.
                bug.status = new_status

                if new_status == 'fixed':

                    bug.fixed_by = user
                    bug.fixed_at = timezone.now()
                    bug.verified_at = None

                elif new_status == 'closed':

                    bug.verified_at = timezone.now()

                elif new_status == 'reopen':

                    # Clear current fix cycle.
                    # Previous fix details remain in status history.
                    bug.fixed_by = None
                    bug.fixed_at = None
                    bug.verified_at = None

                bug.save()

                BugStatusHistory.objects.create(
                    bug=bug,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=user,
                    comment=comment
                )

            return Response(
                {
                    "status": "1",
                    "message": "Bug status updated successfully",
                    "data": BugReportSerializer(
                        bug,
                        context={'request': request}
                    ).data
                },
                status=status.HTTP_200_OK
            )

        except Exception:
            return Response(
                {
                    "status": "0",
                    "message": "Unable to update bug status"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
