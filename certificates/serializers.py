from rest_framework import serializers

from internship.models import Student
from .models import Certificate, CertificateHistory
from django.utils import timezone
import logging
from accounts.models import JobDetail, StaffProfile

logger = logging.getLogger(__name__)

class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'full_name', 'start_date', 'end_date', 'designation', 'email', 'proof_document', 'category', 'status', 'requested_at', 'processed_at']
        read_only_fields = ['requested_at', 'processed_at']

    def validate(self, data):
        # Only validate dates if they are being updated
        if 'end_date' in data and 'start_date' in data and data['end_date'] < data['start_date']:
            raise serializers.ValidationError("End date must be after start date.")
        return data

    def update(self, instance, validated_data):
        try:
            if 'status' in validated_data and validated_data['status'] != instance.status:
                if validated_data['status'] in ['Approved', 'Rejected', 'Issued']:
                    validated_data['processed_at'] = timezone.now()
                elif validated_data['status'] == 'Pending' and instance.processed_at:
                    validated_data['processed_at'] = None
            return super().update(instance, validated_data)
        except Exception as e:
            logger.error(f"Error updating certificate {instance.id}: {str(e)}")
            raise  # Re-raise to propagate the error for debugging

class ManagementStaffSignatureSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.user.first_name", read_only=True)
    # staff_last_name = serializers.CharField(source="staff.user.last_name", read_only=True)
    signature_image = serializers.ImageField(read_only=True)
    department = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = JobDetail
        fields = [
            "staff_name",
            "department",
            "signature_image",
        ]

    def get_staff_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"


class PublicCertificateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = [
            'id', 'full_name', 'email', 'category', 
            'start_date', 'end_date', 'designation', 
            'proof_document', 'requested_at'
        ]
        read_only_fields = ['id', 'requested_at']

    def validate(self, data):
        if 'end_date' in data and 'start_date' in data and data['end_date'] < data['start_date']:
            raise serializers.ValidationError("End date must be after start date.")
        return data

class CertificateHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateHistory
        fields = '__all__'


#-------------------------------------------------------------------------------------------------------------------------------------



from rest_framework import serializers
from .models import CertificateRecord, CertificateSignatory, SignatoryPerson


class SignatoryPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatoryPerson
        fields = ['id', 'name', 'designation', 'signature', 'is_active']


class CertificateSignatorySerializer(serializers.ModelSerializer):
    signatory_detail = SignatoryPersonSerializer(source='signatory', read_only=True)

    class Meta:
        model = CertificateSignatory
        fields = ['id', 'signatory', 'signatory_detail', 'order']


class CertificateRecordSerializer(serializers.ModelSerializer):
    signatories = CertificateSignatorySerializer(many=True, required=False)

    class Meta:
        model = CertificateRecord
        fields = '__all__'
        read_only_fields = ['id', 'issue_date', 'created_at', 'updated_at']

    def create(self, validated_data):
        signatories_data = validated_data.pop('signatories', [])
        certificate = CertificateRecord.objects.create(**validated_data)
        for sig_data in signatories_data:
            CertificateSignatory.objects.create(certificate=certificate, **sig_data)
        return certificate

    def update(self, instance, validated_data):
        signatories_data = validated_data.pop('signatories', None)

        # Update certificate fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update signatories if provided
        if signatories_data is not None:
            instance.signatories.all().delete()
            for sig_data in signatories_data:
                CertificateSignatory.objects.create(certificate=instance, **sig_data)

        return instance

    def validate(self, data):
        certificate_type = data.get('certificate_type')
        user = data.get('user')

        if certificate_type != 'Webinar' and user is None:
            raise serializers.ValidationError(
                {"user": "User is required for non-Webinar certificates."}
            )
        return data
    


class EligibleStudentSerializer(serializers.ModelSerializer):
    full_name  = serializers.SerializerMethodField()
    email      = serializers.SerializerMethodField()
    profile_id = serializers.IntegerField(source='profile.id')
    center     = serializers.StringRelatedField()

    class Meta:
        model = Student
        fields = [
            'id',
            'student_id',
            'profile_id',
            'full_name',
            'email',
            'center',
            'start_date',
            'status',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_email(self, obj):
        return obj.profile.user.email
    
class EligibleStaffSerializer(serializers.ModelSerializer):
    full_name   = serializers.SerializerMethodField()
    email       = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    department  = serializers.SerializerMethodField()
    role        = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = [
            'id',
            'full_name',
            'email',
            'employee_id',
            'department',
            'role',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_email(self, obj):
        return obj.user.email

    def get_employee_id(self, obj):
        return getattr(obj.job_detail, 'employee_id', None)

    def get_department(self, obj):
        job = getattr(obj, 'job_detail', None)
        if job and job.department:
            return job.department.name
        return None

    def get_role(self, obj):
        return getattr(obj.job_detail, 'role', None)