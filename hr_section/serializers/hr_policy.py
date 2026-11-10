import json

from django.db import transaction
from rest_framework import serializers

from ..models import HRPolicy, HRPolicySection, HRPolicySubtitle, HRPolicyPoint


# ---------------------------------------------------------------------------
# Read / leaf serializers
# ---------------------------------------------------------------------------

class HRPolicyPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicyPoint
        fields = ['id', 'title', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class HRPolicySubtitleSerializer(serializers.ModelSerializer):
    points = HRPolicyPointSerializer(many=True, required=False)

    class Meta:
        model = HRPolicySubtitle
        fields = ['id', 'title', 'points', 'created_at']
        read_only_fields = ['id', 'created_at']


class HRPolicySectionSerializer(serializers.ModelSerializer):
    direct_points = HRPolicyPointSerializer(many=True, required=False)
    subtitles = HRPolicySubtitleSerializer(many=True, required=False)

    class Meta:
        model = HRPolicySection
        fields = ['id', 'title', 'content', 'direct_points', 'subtitles', 'created_at']
        read_only_fields = ['id', 'created_at']


# ---------------------------------------------------------------------------
# Policy list / detail
# ---------------------------------------------------------------------------

class HRPolicyListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    sections_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = HRPolicy
        fields = [
            'id', 'title', 'policy_code', 'description', 'effective_date',
            'status', 'status_display', 'document', 'sections_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]

    def get_created_by_name(self, obj):
        user = obj.created_by
        if not user:
            return None
        full_name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
        return full_name or str(user)


class HRPolicyDetailSerializer(HRPolicyListSerializer):
    sections = HRPolicySectionSerializer(many=True, read_only=True)

    class Meta(HRPolicyListSerializer.Meta):
        fields = HRPolicyListSerializer.Meta.fields + ['sections']


# ---------------------------------------------------------------------------
# Nested write (create / patch)
# ---------------------------------------------------------------------------

def create_policy_sections(policy, sections_data):
    """Build Section -> (direct points, Subtitle -> points) tree in creation order."""
    for section_data in sections_data:
        direct_points = section_data.pop('direct_points', [])
        subtitles = section_data.pop('subtitles', [])

        section = HRPolicySection.objects.create(policy=policy, **section_data)

        for point_data in direct_points:
            HRPolicyPoint.objects.create(section=section, **point_data)

        for subtitle_data in subtitles:
            points = subtitle_data.pop('points', [])
            subtitle = HRPolicySubtitle.objects.create(section=section, **subtitle_data)
            for point_data in points:
                HRPolicyPoint.objects.create(subtitle=subtitle, **point_data)


class _HRPolicyWriteBase(serializers.ModelSerializer):
    """
    Accepts `sections` as a JSON list (application/json) or a JSON string
    (multipart/form-data, used when uploading `document`).
    """
    sections = HRPolicySectionSerializer(many=True, required=False)

    class Meta:
        model = HRPolicy
        fields = ['title', 'policy_code', 'description', 'effective_date', 'status', 'document', 'sections']

    def to_internal_value(self, data):
        raw_sections = data.get('sections') if hasattr(data, 'get') else None
        if isinstance(raw_sections, str):
            try:
                parsed = json.loads(raw_sections) if raw_sections.strip() else []
            except ValueError:
                raise serializers.ValidationError({'sections': ['Invalid JSON.']})
            data = {key: data.get(key) for key in data.keys()}
            data['sections'] = parsed
        return super().to_internal_value(data)

    def validate_policy_code(self, value):
        return value or None  # store blank codes as NULL so unique constraint is not hit


class HRPolicyCreateSerializer(_HRPolicyWriteBase):

    @transaction.atomic
    def create(self, validated_data):
        sections_data = validated_data.pop('sections', [])
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user

        policy = HRPolicy.objects.create(**validated_data)
        create_policy_sections(policy, sections_data)
        return policy


class HRPolicyPatchSerializer(_HRPolicyWriteBase):
    """
    PATCH behaviour:
      - `sections` omitted  -> only policy fields are updated, tree untouched.
      - `sections` provided -> the policy's tree is replaced with the given one.
    """

    @transaction.atomic
    def update(self, instance, validated_data):
        sections_data = validated_data.pop('sections', None)
        instance = super().update(instance, validated_data)

        if sections_data is not None:
            instance.sections.all().delete()
            create_policy_sections(instance, sections_data)

        return instance


# ---------------------------------------------------------------------------
# Granular sub-resource serializers (single section / subtitle / point)
# ---------------------------------------------------------------------------

class HRPolicySectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicySection
        fields = ['id', 'policy', 'title', 'content', 'created_at']
        read_only_fields = ['id', 'policy', 'created_at']


class HRPolicySubtitleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicySubtitle
        fields = ['id', 'section', 'title', 'created_at']
        read_only_fields = ['id', 'section', 'created_at']


class HRPolicyPointWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicyPoint
        fields = ['id', 'section', 'subtitle', 'title', 'content', 'created_at']
        read_only_fields = ['id', 'section', 'subtitle', 'created_at']


# Backwards-compatible alias (was exported before the hierarchy was added)
HRPolicySerializer = HRPolicyDetailSerializer
