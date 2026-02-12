from rest_framework import serializers
from .payroll import PayrollListSerializer

class BulkStaffPayrollRequestSerializer(serializers.Serializer):
    staff_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of staff IDs to process."
    )
    period_id = serializers.IntegerField(
        required=True,
        help_text="ID of the PayrollPeriod to process."
    )

class SkippedStaffSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    email = serializers.EmailField(required=False)
    reason = serializers.CharField()

class NotFoundStaffSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    reason = serializers.CharField()

class ResetStaffPayrollSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField(required=True)
    period_id = serializers.IntegerField(required=True)
    generate_now = serializers.BooleanField(required=False, default=False)

class BulkStaffPayrollResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    results = PayrollListSerializer(many=True, required=False)
    skipped = SkippedStaffSerializer(many=True, required=False)
    not_found = NotFoundStaffSerializer(many=True, required=False)
    error = serializers.CharField(required=False)
