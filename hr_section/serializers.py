from rest_framework.serializers import ModelSerializer, CharField, ValidationError
from django.db import transaction

from .models import (
    Enquiry, Designation, JobResponsibility, JobRequirement,
    JobWhyJoinUs, JobPosting, JobApplication
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

class JobWhyJoinUsSerializer(ModelSerializer):
    class Meta:
        model = JobWhyJoinUs
        fields = ['reason']


# JobPosting Create/Update Serializer
class JobPostingCreateSerializer(ModelSerializer):
    responsibilities = JobResponsibilitySerializer(many=True, required=False)
    requirements = JobRequirementSerializer(many=True, required=False)
    benefits = JobWhyJoinUsSerializer(many=True, required=False)

    class Meta:
        model = JobPosting
        fields = [
            'job_title', 'job_type', 'work_mode', 'job_description',
            'more_details', 'status', 'experience_required', 'salery_range',
            'responsibilities', 'requirements', 'benefits','designation',
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

        with transaction.atomic():
            job_posting = JobPosting.objects.create(**validated_data)

            self._create_related_items(job_posting, responsibilities_data, JobResponsibility)
            self._create_related_items(job_posting, requirements_data, JobRequirement)
            self._create_related_items(job_posting, benefits_data, JobWhyJoinUs)

        return job_posting

    def update(self, instance, validated_data):
        responsibilities_data = validated_data.pop('responsibilities', [])
        requirements_data = validated_data.pop('requirements', [])
        benefits_data = validated_data.pop('benefits', [])

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
