from rest_framework import serializers
from django.db import transaction

from ..models import (
    OfferLetter,
    OfferLetterSection,
    OfferLetterSubtitle,
    OfferLetterPoint,
)


def create_offer_sections(offer, sections_data):
    for section_data in sections_data:
        subtitles_data = section_data.pop("subtitles", [])

        section = OfferLetterSection.objects.create(
            offer_letter=offer,
            **section_data
        )

        for subtitle_data in subtitles_data:
            points_data = subtitle_data.pop("points", [])

            subtitle = OfferLetterSubtitle.objects.create(
                section=section,
                **subtitle_data
            )

            for point_data in points_data:
                OfferLetterPoint.objects.create(
                    subtitle=subtitle,
                    **point_data
                )


class OfferLetterPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferLetterPoint
        fields = ["id", "content", "order"]


class OfferLetterSubtitleSerializer(serializers.ModelSerializer):
    points = OfferLetterPointSerializer(many=True, required=False)

    class Meta:
        model = OfferLetterSubtitle
        fields = ["id", "title", "order", "points"]


class OfferLetterSectionSerializer(serializers.ModelSerializer):
    subtitles = OfferLetterSubtitleSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = OfferLetterSection
        fields = ["id", "title", "content", "order", "subtitles"]


class OfferLetterCreateSerializer(serializers.ModelSerializer):
    sections = OfferLetterSectionSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = OfferLetter
        exclude = ["created_by", "created_at", "updated_at"]

    def validate_responsibilities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "responsibilities must be a list of strings."
            )

        if any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError(
                "Each responsibility must be a string."
            )

        return value

    def validate_allowances(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("allowances must be a list.")

        for allowance in value:
            if not isinstance(allowance, dict):
                raise serializers.ValidationError(
                    "Each allowance must be an object."
                )

            if not allowance.get("name"):
                raise serializers.ValidationError(
                    "Each allowance must have a name."
                )

            if "amount" not in allowance:
                raise serializers.ValidationError(
                    "Each allowance must have an amount."
                )

            try:
                amount = float(allowance["amount"])
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    "Allowance amount must be a valid number."
                )

            if amount < 0:
                raise serializers.ValidationError(
                    "Allowance amount cannot be negative."
                )

        return value

    def validate(self, attrs):
        if attrs.get("is_target_based") and not attrs.get("target_details"):
            raise serializers.ValidationError({
                "target_details": (
                    "target_details is required when is_target_based is True."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        sections_data = validated_data.pop("sections", [])
        request = self.context.get("request")

        validated_data["created_by"] = (
            request.user if request else None
        )

        offer = OfferLetter.objects.create(**validated_data)
        create_offer_sections(offer, sections_data)

        return offer


class OfferLetterPatchSerializer(serializers.ModelSerializer):
    sections = OfferLetterSectionSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = OfferLetter
        exclude = ["created_by", "created_at", "updated_at"]

    def validate_responsibilities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "responsibilities must be a list of strings."
            )

        if any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError(
                "Each responsibility must be a string."
            )

        return value

    def validate_allowances(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("allowances must be a list.")

        for allowance in value:
            if not isinstance(allowance, dict):
                raise serializers.ValidationError(
                    "Each allowance must be an object."
                )

            if not allowance.get("name"):
                raise serializers.ValidationError(
                    "Each allowance must have a name."
                )

            if "amount" not in allowance:
                raise serializers.ValidationError(
                    "Each allowance must have an amount."
                )

            try:
                amount = float(allowance["amount"])
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    "Allowance amount must be a valid number."
                )

            if amount < 0:
                raise serializers.ValidationError(
                    "Allowance amount cannot be negative."
                )

        return value

    def validate(self, attrs):
        instance = self.instance

        is_target_based = attrs.get(
            "is_target_based",
            instance.is_target_based
        )

        target_details = attrs.get(
            "target_details",
            instance.target_details
        )

        if is_target_based and not target_details:
            raise serializers.ValidationError({
                "target_details": (
                    "target_details is required when is_target_based is True."
                )
            })

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        sections_data = validated_data.pop("sections", None)

        instance = super().update(instance, validated_data)

        if sections_data is not None:
            instance.sections.all().delete()
            create_offer_sections(instance, sections_data)

        return instance


class OfferLetterListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list endpoint.
    """
    created_by = serializers.StringRelatedField()
    monthly_salary = serializers.SerializerMethodField()

    class Meta:
        model = OfferLetter
        fields = [
            "id",
            "candidate_name",
            "candidate_email",
            "job_title",
            "status",
            "duty_type",
            "basic_salary",
            "monthly_salary",
            "joining_date",
            "company_name",
            "phone_number",
            "created_by",
            "created_at",
        ]

    def get_total_allowance(self, obj):
        total = 0
        for allowance in obj.allowances or []:
            if not isinstance(allowance, dict):
                continue
            try:
                total += float(allowance.get("amount", 0))
            except (TypeError, ValueError):
                continue
        return total

    def get_monthly_salary(self, obj):
        total = self.get_total_allowance(obj) + float(obj.basic_salary or 0)
        return total


class OfferLetterDetailSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )

    duty_type_display = serializers.CharField(
        source="get_duty_type_display",
        read_only=True
    )

    total_allowance = serializers.SerializerMethodField()
    monthly_salary = serializers.SerializerMethodField()

    sections = OfferLetterSectionSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = OfferLetter
        fields = "__all__"

    def get_total_allowance(self, obj):
        total = 0
        for allowance in obj.allowances or []:
            if not isinstance(allowance, dict):
                continue
            try:
                total += float(allowance.get("amount", 0))
            except (TypeError, ValueError):
                continue
        return total

    def get_monthly_salary(self, obj):
        return (
            self.get_total_allowance(obj)
            + float(obj.basic_salary or 0)
        )


class OfferLetterShareSerializer(serializers.Serializer):
    email = serializers.EmailField()
    subject = serializers.CharField(
        max_length=255
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True
    )
    pdf = serializers.FileField()

    def validate_pdf(self, value):
        if value.content_type != "application/pdf":
            raise serializers.ValidationError(
                "Only PDF files are allowed."
            )
        return value

