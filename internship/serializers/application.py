import re

from django.db import transaction
from rest_framework import serializers

from ..models import InternshipApplication, InternshipDocument


class InternshipDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternshipDocument
        fields = ["id", "document_type", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class InternshipApplicationSerializer(serializers.ModelSerializer):
    documents = InternshipDocumentSerializer(many=True, required=False)

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
            "address",
            "state",
            "district",
            "pincode",
            "where_did_you_find_us",
            "other_source",
            "course_applied_for",
            "course_duration",
            "course_type",
            "linkedin_profile_url",
            "github_profile_url",
            "portfolio_url",
            "academic_counselor",
            "documents",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

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

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        documents_data = validated_data.pop("documents", [])

        application = InternshipApplication(**validated_data)
        application.full_clean()
        application.save()

        for document_data in documents_data:
            document = InternshipDocument(application=application, **document_data)
            document.full_clean()
            document.save()

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
            "course_applied_for",
            "course_duration",
            "course_type",
            "linkedin_profile_url",
            "github_profile_url",
            "portfolio_url",
            "academic_counselor",
            "created_at",
        ]
