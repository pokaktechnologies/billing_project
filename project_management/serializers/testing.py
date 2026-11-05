
from rest_framework import serializers

from ..models.testing import BugReport


class BugReportSerializer(serializers.ModelSerializer):

    project_name = serializers.CharField(
        source='project.project_name',
        read_only=True
    )

    reported_by_name = serializers.CharField(
        source='reported_by.first_name',
        read_only=True
    )

    fixed_by_name = serializers.CharField(
        source='fixed_by.first_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = BugReport

        fields = [
            'id',
            'bug_id',

            'project',
            'project_name',

            'module',
            'title',

            'steps_to_reproduce',
            'expected_result',
            'actual_result',

            'screenshot',

            'severity',
            'status',

            'reported_by',
            'reported_by_name',

            'fixed_by',
            'fixed_by_name',

            'created_at',
            'updated_at',

            'fixed_at',
            'verified_at',
        ]

        read_only_fields = [
            'id',
            'bug_id',
            'status',

            'reported_by',
            'reported_by_name',

            'fixed_by',
            'fixed_by_name',

            'created_at',
            'updated_at',

            'fixed_at',
            'verified_at',
        ]
