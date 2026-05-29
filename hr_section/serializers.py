from rest_framework.serializers import ModelSerializer, CharField, ValidationError
from django.db import transaction

from .models import (
    Enquiry, Designation, JobResponsibility, JobRequirement,
    JobWhyJoinUs, JobPosting, JobApplication, JobPostingSkill
)

# Enquiry Serializers
class EnquirySerializer(ModelSerializer):
    class Meta:
        model = Enquiry
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class EnquiryStatusUpdateSerializer(ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ['status']


# Designation Serializer
class DesignationSerializer(ModelSerializer):
    class Meta:
        model = Designation
        fields = '__all__'
        read_only_fields = ('created_at',)


# Related Serializers
class JobResponsibilitySerializer(ModelSerializer):
    class Meta:
        model = JobResponsibility
        fields = ['responsibility']

class JobRequirementSerializer(ModelSerializer):
    class Meta:
        model = JobRequirement
        fields = ['requirement']

class JobSkillSerializer(ModelSerializer):
    class Meta:
        model = JobPostingSkill
        fields = ['skill']

class JobWhyJoinUsSerializer(ModelSerializer):
    class Meta:
        model = JobWhyJoinUs
        fields = ['reason']


# JobPosting Create/Update Serializer
class JobPostingCreateSerializer(ModelSerializer):
    responsibilities = JobResponsibilitySerializer(many=True, required=False)
    requirements = JobRequirementSerializer(many=True, required=False)
    benefits = JobWhyJoinUsSerializer(many=True, required=False)
    skill = JobSkillSerializer(many=True, required=False)

    class Meta:
        model = JobPosting
        fields = [
            'job_title', 'job_type', 'work_mode', 'job_description',
            'more_details', 'status', 'experience_required', 'salery_range',
            'responsibilities', 'requirements', 'benefits', 'designation', 'education','skill'
        ]

    def validate(self, attrs):
        if not attrs.get('job_title'):
            raise ValidationError("Job title is required.")
        if not attrs.get('job_description'):
            raise ValidationError("Job description is required.")
        if not attrs.get('designation'):
            raise ValidationError("Designation is required.")
        return attrs

    def create(self, validated_data):
        responsibilities_data = validated_data.pop('responsibilities', [])
        requirements_data = validated_data.pop('requirements', [])
        benefits_data = validated_data.pop('benefits', [])
        skills_data = validated_data.pop('skill', [])

        with transaction.atomic():
            job_posting = JobPosting.objects.create(**validated_data)

            self._create_related_items(job_posting, responsibilities_data, JobResponsibility)
            self._create_related_items(job_posting, requirements_data, JobRequirement)
            self._create_related_items(job_posting, benefits_data, JobWhyJoinUs)
            self._create_related_items(job_posting, skills_data, JobPostingSkill)

        return job_posting

    def update(self, instance, validated_data):
        responsibilities_data = validated_data.pop('responsibilities', [])
        requirements_data = validated_data.pop('requirements', [])
        benefits_data = validated_data.pop('benefits', [])
        skills_data = validated_data.pop('skill', [])

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if responsibilities_data:
                instance.responsibilities.all().delete()
                self._create_related_items(instance, responsibilities_data, JobResponsibility)

            if requirements_data:
                instance.requirements.all().delete()
                self._create_related_items(instance, requirements_data, JobRequirement)

            if benefits_data:
                instance.benefits.all().delete()
                self._create_related_items(instance, benefits_data, JobWhyJoinUs)
            
            if skills_data:
                instance.skills.all().delete()
                self._create_related_items(instance, skills_data, JobPostingSkill)

        return instance

    def _create_related_items(self, job_posting, items_data, model_class):
        model_class.objects.bulk_create([
            model_class(job_posting=job_posting, **item) for item in items_data
        ])


# JobPosting List Serializer
class JobPostingListSerializer(ModelSerializer):
    designation = CharField(source='designation.name', read_only=True)
    class Meta:
        model = JobPosting
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


# JobPosting Detail Serializer (Read-only)
class JobPostingSerializer(ModelSerializer):
    responsibilities = JobResponsibilitySerializer(many=True, read_only=True)
    requirements = JobRequirementSerializer(many=True, read_only=True)
    benefits = JobWhyJoinUsSerializer(many=True, read_only=True)
    skills = JobSkillSerializer(many=True, read_only=True)

    class Meta:
        model = JobPosting
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


# Job Application Serializers
class JobApplicationSerializer(ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'experience', 'resume', 'job', 'applied_at',
        ]
        read_only_fields = ['id', 'applied_at', 'job']

    def create(self, validated_data):
        job_posting = self.context.get('job')
        if not job_posting:
            raise ValidationError("Job posting is required for application.")
        
        designation = job_posting.designation
        return JobApplication.objects.create(
            job=job_posting,
            designation=designation,
            **validated_data
        )

class JobApplicationWithoutJobSerializer(ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'designation', 'experience', 'resume', 'job', 'applied_at',
        ]
        read_only_fields = ['id', 'applied_at', 'job']

class JobApplicationDisplaySerializer(ModelSerializer):
    designation = CharField(source='designation.name', read_only=True)
    job = JobPostingListSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'designation', 'experience', 'resume', 'job', 'applied_at', 'status'
        ]
        read_only_fields = ['id']


class JobApplicationListSerializer(ModelSerializer):
    designation = CharField(source='designation.name', read_only=True)
    class Meta:
        model = JobApplication
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'designation', 'experience', 'resume', 'job', 'applied_at', 'status'
        ]
        read_only_fields = ['id', 'applied_at', 'job', 'status']


class JobApplicationStatusUpdateSerializer(ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['status']

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        return instance



# ERP Enquiry
from .models import ErpEnquiry


class ErpEnquirySerializer(ModelSerializer):
    class Meta:
        model = ErpEnquiry
        fields = '__all__'
        read_only_fields = ['status', 'created_at', 'updated_at']

class ErpEnquiryStatusUpdateSerializer(ModelSerializer):
    class Meta:
        model = ErpEnquiry
        fields = ['status']


#OFFER LETTER

from rest_framework import serializers
from .models import OfferLetter, StatusChoices, DutyTypeChoices


class OfferLetterCreateSerializer(serializers.ModelSerializer):
    """
    Used for POST (create) — all writable fields.
    """

    class Meta:
        model = OfferLetter
        exclude = ["created_by", "created_at", "updated_at"]

    # ── Validations ──────────────────────────────────────────────────────────

    def validate_responsibilities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("responsibilities must be a list of strings.")
        if any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError("Each responsibility must be a string.")
        return value

    def validate(self, attrs):
        # If target-based, target_details should be provided
        if attrs.get("is_target_based") and not attrs.get("target_details"):
            raise serializers.ValidationError(
                {"target_details": "target_details is required when is_target_based is True."}
            )
        # basic_salary should not exceed monthly_salary
        basic = attrs.get("basic_salary")
        monthly = attrs.get("monthly_salary")
        if basic and monthly and basic > monthly:
            raise serializers.ValidationError(
                {"basic_salary": "basic_salary cannot be greater than monthly_salary."}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["created_by"] = request.user if request else None
        return super().create(validated_data)


class OfferLetterPatchSerializer(serializers.ModelSerializer):
    """
    Used for PATCH (partial update) — same fields, all optional.
    """

    class Meta:
        model = OfferLetter
        exclude = ["created_by", "created_at", "updated_at"]
        extra_kwargs = {field: {"required": False} for field in [
            "candidate_name", "job_title", "monthly_salary", "joining_date", "company_name"
        ]}

    def validate_responsibilities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("responsibilities must be a list of strings.")
        if any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError("Each responsibility must be a string.")
        return value

    def validate(self, attrs):
        instance = self.instance

        is_target_based = attrs.get("is_target_based", instance.is_target_based)
        target_details  = attrs.get("target_details", instance.target_details)
        if is_target_based and not target_details:
            raise serializers.ValidationError(
                {"target_details": "target_details is required when is_target_based is True."}
            )

        basic   = attrs.get("basic_salary", instance.basic_salary)
        monthly = attrs.get("monthly_salary", instance.monthly_salary)
        if basic and monthly and basic > monthly:
            raise serializers.ValidationError(
                {"basic_salary": "basic_salary cannot be greater than monthly_salary."}
            )
        return attrs


class OfferLetterListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list endpoint.
    """
    created_by = serializers.StringRelatedField()

    class Meta:
        model = OfferLetter
        fields = [
            "id",
            "candidate_name",
            "candidate_email",
            "job_title",
            "status",
            "duty_type",
            "monthly_salary",
            "joining_date",
            "company_name",
            "created_by",
            "created_at",
        ]


class OfferLetterDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for retrieve endpoint.
    """
    created_by      = serializers.StringRelatedField()
    status_display   = serializers.CharField(source="get_status_display", read_only=True)
    duty_type_display = serializers.CharField(source="get_duty_type_display", read_only=True)

    class Meta:
        model = OfferLetter
        fields = "__all__"