from rest_framework import serializers
from ..models import LeaveRequest
from accounts.models import StaffProfile
from django.utils import timezone

class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    action_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            'id',
            'staff',
            'staff_name',
            'start_date',
            'end_date',
            'reason',
            'status',
            'requested_at',
            'actioned_at',
            'action_by',
            'action_by_name'
        ]
        read_only_fields = [
            'staff',
            'status',
            'requested_at',
            'actioned_at',
            'action_by',
            'action_by_name'
        ]
    
    def get_staff_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"
    
    def get_action_by_name(self, obj):
        return f"{obj.action_by.user.first_name} {obj.action_by.user.last_name}" if obj.action_by else None

    def validate(self, data):
        request = self.context.get('request')
        staff = request.user.staff_profile

        # For partial updates, fall back to existing instance values
        start_date = data.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = data.get('end_date', getattr(self.instance, 'end_date', None))

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })
        # Check for overlapping leave requests
        # Run always on create; on update only when dates are being changed
        should_check = not self.instance or 'start_date' in data or 'end_date' in data
        if should_check and start_date and end_date:
            # Two ranges overlap when: start_a <= end_b AND end_a >= start_b
            qs = LeaveRequest.objects.filter(
                staff=staff,
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Leave request overlaps with an existing leave for this date range."
                )

        return data

    def create(self, validated_data):
        staff = self.context['request'].user.staff_profile
        validated_data['staff'] = staff
        return super().create(validated_data)


class HrLeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    action_by_name = serializers.SerializerMethodField()
    leave_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id',
            'staff',
            'staff_name',
            'start_date',
            'end_date',
            'reason',
            'status',
            'leave_days',
            'requested_at',
            'actioned_at',
            'action_by',
            'action_by_name'
        ]
        read_only_fields = [
            'requested_at',
            'actioned_at',
            'action_by',
            'action_by_name'
        ]
    def get_staff_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"
    
    def get_action_by_name(self, obj):
        return f"{obj.action_by.user.first_name} {obj.action_by.user.last_name}" if obj.action_by else None
    def validate(self, data):
        # Get staff from payload or existing instance
        staff = data.get('staff', getattr(self.instance, 'staff', None))

        # For partial updates, fall back to existing instance values
        start_date = data.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = data.get('end_date', getattr(self.instance, 'end_date', None))

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })

        # Check for overlapping leave requests
        should_check = not self.instance or 'start_date' in data or 'end_date' in data
        if should_check and start_date and end_date and staff:
            qs = LeaveRequest.objects.filter(
                staff=staff,
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Leave request overlaps with an existing leave for this date range."
                )

        return data

    def create(self, validated_data):
        request = self.context['request']
        validated_data['actioned_at'] = timezone.now()
        validated_data['action_by'] = getattr(request.user, 'staff_profile', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context['request']
        # Auto-set actioned_at and action_by when status changes
        if 'status' in validated_data and validated_data['status'] != instance.status:
            validated_data['actioned_at'] = timezone.now()
            validated_data['action_by'] = getattr(request.user, 'staff_profile', None)
        return super().update(instance, validated_data)

