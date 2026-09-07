import re

from django.core.mail import send_mail
from django.db import transaction
from rest_framework import serializers
from django.conf import settings
from ..models import PAYMENT_METHODS, Batch, InstallmentPlan, InternshipApplication, InternshipDocument, StudentCourseEnrollment


class InternshipDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternshipDocument
        fields = ["id", "document_type", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class InternshipApplicationSerializer(serializers.ModelSerializer):
    documents = InternshipDocumentSerializer(many=True, required=False)
    # academic_counselor_name = serializers.CharField(source="academic_counselor.get_full_name", read_only=True)
    councellor_name = serializers.CharField(source="councellor.get_full_name", read_only=True)
    courses_name = serializers.CharField(source="course.title", read_only=True)
    class Meta:
        model = InternshipApplication
        fields = [
            "id",
            "first_name",
            "last_name",
            "profile_image",
            "primary_phone",
            "secondary_phone",
            "email",
            "dob",
            "gender",
            "qualification",
            "course_name",
            "courses_name",
            "address",
            "state",
            "district",
            "pincode",
            "where_did_you_find_us",
            "other_source",
            # "course_applied_for",
            "course",
            "course_duration",
            "course_type",
            "linkedin_profile_url",
            "github_profile_url",
            "portfolio_url",
            # "academic_counselor",
            # "academic_counselor_name",
             "councellor",
            "councellor_name",
            "documents",
            "created_at",
            "form_type",
            "slot_amount",
            "slot_payment_method",
            "slot_transaction_id",
            "slot_payment_date",
            "is_converted",
            "converted_students",
        ]
        read_only_fields = ["id", "created_at", "is_converted", "converted_students"]

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)

        multipart_documents = self._extract_documents_from_request()
        if multipart_documents is not None:
            internal_value["documents"] = self.fields["documents"].run_validation(
                multipart_documents
            )

        return internal_value

    def validate(self, attrs):
        where_did_you_find_us = attrs.get("where_did_you_find_us")
        other_source = attrs.get("other_source")

        if where_did_you_find_us == "other" and not other_source:
            raise serializers.ValidationError(
                {"other_source": "This field is required when 'other' is selected."}
            )

        if where_did_you_find_us != "other" and other_source:
            raise serializers.ValidationError(
                {
                    "other_source": (
                        "This field should only be provided when "
                        "'where_did_you_find_us' is 'other'."
                    )
                }
            )
        
        form_type = attrs.get("form_type")

        if form_type == "free_course_form":

            attrs["slot_amount"] = None
            attrs["slot_payment_method"] = None
            attrs["slot_transaction_id"] = None
            attrs["slot_payment_date"] = None

        elif form_type == "internship_form":

            slot_amount = attrs.get("slot_amount")

            if slot_amount is not None and slot_amount < 0:
                raise serializers.ValidationError({
                    "slot_amount": "Slot amount cannot be negative."
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        documents_data = validated_data.pop("documents", [])

        application = InternshipApplication(**validated_data)
        application.full_clean()
        application.save()

        for document_data in documents_data:
            document = InternshipDocument(
                application=application,
                **document_data
            )
            document.full_clean()
            document.save()

        # -----------------------------------------
        # Send confirmation email
        # -----------------------------------------
        try:

            subject = "Internship Application Submitted Successfully"

            message = f"""
    Dear {application.first_name} {application.last_name},

    Thank you for submitting your internship application with Pokak Technologies.

    Application Details

    Name:
    {application.first_name} {application.last_name}

    Course:
    {application.course}

    Course Type:
    {application.course_type}

    Duration:
    {application.course_duration} Month(s)

    """

            if application.form_type == "internship_form":
                message += f"""
    Slot Amount:
    ₹{application.slot_amount or 0}
    """

            message += """

    Our team will review your application and contact you shortly.

    Thank you.

    Regards,
    Pokak Technologies
    """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                fail_silently=False,
            )

        except Exception as e:
            print("Email sending failed:", e)

        return application

    def _extract_documents_from_request(self):
        request = self.context.get("request")
        if request is None:
            return None

        content_type = request.content_type or ""
        if "multipart/form-data" not in content_type:
            return None

        indexed_documents = self._extract_indexed_documents(request)
        if indexed_documents is not None:
            return indexed_documents

        return self._extract_parallel_documents(request)

    def _extract_indexed_documents(self, request):
        key_patterns = [
            re.compile(r"^documents\[(\d+)\]\[(file|document_type)\]$"),
            re.compile(r"^documents\[(\d+)\]\.(file|document_type)$"),
            re.compile(r"^documents\.(\d+)\.(file|document_type)$"),
        ]

        indexed_documents = {}

        for source in (request.data, request.FILES):
            for key in source.keys():
                for pattern in key_patterns:
                    match = pattern.match(key)
                    if not match:
                        continue

                    index = int(match.group(1))
                    field_name = match.group(2)
                    indexed_documents.setdefault(index, {})
                    indexed_documents[index][field_name] = source.get(key)
                    break

        if not indexed_documents:
            return None

        ordered_indices = sorted(indexed_documents.keys())
        expected_indices = list(range(len(ordered_indices)))
        if ordered_indices != expected_indices:
            raise serializers.ValidationError(
                {
                    "documents": (
                        "Document indexes must be contiguous and start from 0."
                    )
                }
            )

        return [indexed_documents[index] for index in ordered_indices]

    def _extract_parallel_documents(self, request):
        document_files = request.FILES.getlist("document_files")
        document_types = request.data.getlist("document_types")

        if not document_files and not document_types:
            return None

        if len(document_files) != len(document_types):
            raise serializers.ValidationError(
                {
                    "documents": (
                        "Each uploaded document must include a matching "
                        "'document_type'."
                    )
                }
            )

        return [
            {"file": document_file, "document_type": document_type}
            for document_file, document_type in zip(document_files, document_types)
        ]


class InternshipApplicationListSerializer(InternshipApplicationSerializer):
    
    class Meta(InternshipApplicationSerializer.Meta):
        fields = [
            "id",
            "first_name",
            "last_name",
            "profile_image",
            "primary_phone",
            "secondary_phone",
            "email",
            "dob",
            "gender",
            "qualification",
            "course_name",
            "address",
            "state",
            "district",
            "pincode",
            "where_did_you_find_us",
            "other_source",
            # "course_applied_for",
            "course",
            "courses_name",
            "course_duration",
            "course_type",
            "linkedin_profile_url",
            "github_profile_url",
            "portfolio_url",
            # "academic_counselor",
             "councellor",
            "councellor_name",
            "created_at",
            "slot_amount",
            "is_converted",
        ]


from rest_framework import serializers

from ..models import Center, SalesPerson


class ConvertToStudentSerializer(serializers.Serializer):

    center = serializers.PrimaryKeyRelatedField(
        queryset=Center.objects.all()
    )

    start_date = serializers.DateField()

    councellor = serializers.PrimaryKeyRelatedField(
        queryset=SalesPerson.objects.all(),
        required=False,
        allow_null=True,
    )

    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("inactive", "Inactive"),
    ]

    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        default="active"
    )

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        min_length=6
    )

    confirm_password = serializers.CharField(
        write_only=True
    )


    enrollment_batch = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.none(),
        required=False,
        allow_null=True,
    )

    enrollment_payment_plan_type = serializers.ChoiceField(
        choices=StudentCourseEnrollment.PAYMENT_PLAN_TYPES,
        required=False,# ippo use akkathond false use aakuvaaneeel true aakkanam
    )

    enrollment_installment_plan = serializers.PrimaryKeyRelatedField(
        queryset=InstallmentPlan.objects.all(),
        required=False,
        allow_null=True,
    )

    enrollment_custom_installments = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )

    enrollment_advance_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
    )

    enrollment_payment_method = serializers.ChoiceField(
        choices=PAYMENT_METHODS,
        required=False,
        allow_null=True,
    )

    enrollment_transaction_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    enrollment_payment_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    enrollment_discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
    )

    enrollment_discount_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    enrollment_receipt = serializers.JSONField(
        required=False,
        allow_null=True,
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        application = self.context.get("application")

        if application and application.course:
            self.fields["enrollment_batch"].queryset = Batch.objects.filter(
                course=application.course
            )
    def validate(self, attrs):

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password":
                    "Passwords do not match."
            })

        return attrs


class InternshipApplicationReportSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    counsellor_id = serializers.SerializerMethodField()
    counsellor_name = serializers.SerializerMethodField()
    course_id = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    qualification_display = serializers.CharField(source="get_qualification_display", read_only=True)
    course_type_display = serializers.CharField(source="get_course_type_display", read_only=True)
    where_did_you_find_us_display = serializers.CharField(source="get_where_did_you_find_us_display", read_only=True)
    form_type_display = serializers.CharField(source="get_form_type_display", read_only=True)
    converted_student_id = serializers.SerializerMethodField()
    converted_student_code = serializers.SerializerMethodField()
    documents_count = serializers.SerializerMethodField()
    documents = InternshipDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = InternshipApplication
        fields = [
            "id",
            "form_type",
            "form_type_display",
            "first_name",
            "last_name",
            "applicant_name",
            "profile_image",
            "primary_phone",
            "secondary_phone",
            "email",
            "dob",
            "gender",
            "gender_display",
            "qualification",
            "qualification_display",
            "course_name",
            "address",
            "state",
            "district",
            "pincode",
            "where_did_you_find_us",
            "where_did_you_find_us_display",
            "other_source",
            "course_id",
            "course_title",
            "course_duration",
            "course_type",
            "course_type_display",
            "linkedin_profile_url",
            "github_profile_url",
            "portfolio_url",
            "counsellor_id",
            "counsellor_name",
            "slot_amount",
            "slot_payment_method",
            "slot_transaction_id",
            "slot_payment_date",
            "is_converted",
            "converted_student_id",
            "converted_student_code",
            "documents_count",
            "documents",
            "created_at",
        ]

    def get_applicant_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_counsellor_id(self, obj):
        return obj.councellor.id if obj.councellor else None

    def get_counsellor_name(self, obj):
        if obj.councellor:
            return obj.councellor.get_full_name()
        return obj.academic_counselor or None

    def get_course_id(self, obj):
        return obj.course.id if obj.course else None

    def get_course_title(self, obj):
        if obj.course:
            return obj.course.title
        return obj.course_applied_for or obj.course_name or None

    def get_converted_student_id(self, obj):
        return obj.converted_students.id if obj.converted_students else None

    def get_converted_student_code(self, obj):
        return obj.converted_students.student_id if obj.converted_students else None

    def get_documents_count(self, obj):
        return obj.documents.count()
