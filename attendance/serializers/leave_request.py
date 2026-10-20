from rest_framework import serializers
from ..models import LeaveRequest
from accounts.models import StaffProfile
from django.utils import timezone
from datetime import datetime, timedelta


class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_name= serializers.SerializerMethodField()
    action_by_name = serializers.SerializerMethodField()
    leave_days = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "staff",
            "staff_name",
            "start_date",
            "end_date",
            "is_half_day",
            "start_time",
            "end_time",
            "duration_hours",
            "leave_days",
            "reason",
            "status",
            "requested_at",
            "actioned_at",
            "action_by",
            "action_by_name",
        ]

        read_only_fields = [
            "staff",
            "status",
            "requested_at",
            "actioned_at",
            "action_by",
            "action_by_name",
            "leave_days",
            "duration_hours",
        ]

    def get_staff_name(self, obj):
        return (
            f"{obj.staff.user.first_name} "
            f"{obj.staff.user.last_name}"
        )

    def get_action_by_name(self, obj):
        if obj.action_by:
            return (
                f"{obj.action_by.user.first_name} "
                f"{obj.action_by.user.last_name}"
            )
        return None

    def get_leave_days(self, obj):
        return obj.leave_days

    def get_duration_hours(self, obj):
        return obj.duration_hours

    def validate(self, data):
        request = self.context.get("request")
        staff = request.user.staff_profile

        start_date = data.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = data.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        is_half_day = data.get(
            "is_half_day",
            getattr(self.instance, "is_half_day", False),
        )

        start_time = data.get(
            "start_time",
            getattr(self.instance, "start_time", None),
        )
        end_time = data.get(
            "end_time",
            getattr(self.instance, "end_time", None),
        )

        # Clear old times when changing to normal leave.
        if "is_half_day" in data and not is_half_day:
            data["start_time"] = None
            data["end_time"] = None
            start_time = None
            end_time = None

        # Validate date range.
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })

        if is_half_day:
            if not start_date or not end_date:
                raise serializers.ValidationError({
                    "end_date": "Start date and end date are required."
                })

            if start_date != end_date:
                raise serializers.ValidationError({
                    "end_date": "Half-day leave must be for one date only."
                })

            if not start_time:
                raise serializers.ValidationError({
                    "start_time": "Start time is required for half-day leave."
                })

            if not end_time:
                raise serializers.ValidationError({
                    "end_time": "End time is required for half-day leave."
                })

            start_datetime = datetime.combine(start_date, start_time)
            end_datetime = datetime.combine(end_date, end_time)

            if end_datetime <= start_datetime:
                raise serializers.ValidationError({
                    "end_time": "End time must be after start time."
                })

        else:
            # Normal leave must not retain half-day times.
            if start_time or end_time:
                raise serializers.ValidationError({
                    "start_time": (
                        "Time duration is only allowed for half-day leave."
                    )
                })

        # Check overlapping leave requests.
        should_check = (
            not self.instance
            or "start_date" in data
            or "end_date" in data
            or "is_half_day" in data
        )

        if should_check and start_date and end_date:
            queryset = LeaveRequest.objects.filter(
                staff=staff,
                start_date__lte=end_date,
                end_date__gte=start_date,
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "Leave request overlaps with an existing leave "
                    "for this date range."
                )

        return data

    def create(self, validated_data):
        validated_data["staff"] = (
            self.context["request"].user.staff_profile
        )
        return super().create(validated_data)



class HrLeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    action_by_name = serializers.SerializerMethodField()
    leave_days = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "staff",
            "staff_name",
            "start_date",
            "end_date",
            "is_half_day",
            "start_time",
            "end_time",
            "duration_hours",
            "leave_days",
            "reason",
            "status",
            "requested_at",
            "actioned_at",
            "action_by",
            "action_by_name",
        ]

        read_only_fields = [
            "requested_at",
            "actioned_at",
            "action_by",
            "action_by_name",
            "leave_days",
            "duration_hours",
        ]

    def get_staff_name(self, obj):
        return (
            f"{obj.staff.user.first_name} "
            f"{obj.staff.user.last_name}"
        )

    def get_action_by_name(self, obj):
        if obj.action_by:
            return (
                f"{obj.action_by.user.first_name} "
                f"{obj.action_by.user.last_name}"
            )
        return None

    def get_leave_days(self, obj):
        return obj.leave_days

    def get_duration_hours(self, obj):
        return obj.duration_hours

    def validate(self, data):
        staff = data.get(
            "staff",
            getattr(self.instance, "staff", None),
        )

        start_date = data.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = data.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        is_half_day = data.get(
            "is_half_day",
            getattr(self.instance, "is_half_day", False),
        )

        start_time = data.get(
            "start_time",
            getattr(self.instance, "start_time", None),
        )
        end_time = data.get(
            "end_time",
            getattr(self.instance, "end_time", None),
        )

        # Clear times when converting half-day to normal leave.
        if "is_half_day" in data and not is_half_day:
            data["start_time"] = None
            data["end_time"] = None
            start_time = None
            end_time = None

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })

        if is_half_day:
            if not start_date or not end_date or start_date != end_date:
                raise serializers.ValidationError({
                    "end_date": "Half-day leave must be for one date only."
                })

            if not start_time:
                raise serializers.ValidationError({
                    "start_time": "Start time is required for half-day leave."
                })

            if not end_time:
                raise serializers.ValidationError({
                    "end_time": "End time is required for half-day leave."
                })

            start_datetime = datetime.combine(start_date, start_time)
            end_datetime = datetime.combine(end_date, end_time)

            if end_datetime <= start_datetime:
                raise serializers.ValidationError({
                    "end_time": "End time must be after start time."
                })

        elif start_time or end_time:
            raise serializers.ValidationError({
                "start_time": (
                    "Time duration is only allowed for half-day leave."
                )
            })

        # Check overlapping leave requests.
        should_check = (
            not self.instance
            or "start_date" in data
            or "end_date" in data
            or "is_half_day" in data
            or "staff" in data
        )

        if should_check and start_date and end_date and staff:
            queryset = LeaveRequest.objects.filter(
                staff=staff,
                start_date__lte=end_date,
                end_date__gte=start_date,
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "Leave request overlaps with an existing leave "
                    "for this date range."
                )

        return data

    def create(self, validated_data):
        request = self.context["request"]

        validated_data["actioned_at"] = timezone.now()
        validated_data["action_by"] = getattr(
            request.user,
            "staff_profile",
            None,
        )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context["request"]

        if (
            "status" in validated_data
            and validated_data["status"] != instance.status
        ):
            validated_data["actioned_at"] = timezone.now()
            validated_data["action_by"] = getattr(
                request.user,
                "staff_profile",
                None,
            )

        return super().update(instance, validated_data)
