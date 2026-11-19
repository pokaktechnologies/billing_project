from rest_framework import serializers


class PendingWorkItemSerializer(serializers.Serializer):
    """
    Standard schema for a single actionable pending work item.
    Designed for easy cross-module unification.
    """
    id = serializers.CharField(help_text="Unique composite ID for frontend key rendering, e.g. 'reg_app_12'")
    record_id = serializers.IntegerField(allow_null=True, required=False, help_text="Database PK of the underlying record")
    tab = serializers.CharField(help_text="Submodule tab key, e.g. 'registration_form', 'admissions'")
    tab_label = serializers.CharField(help_text="Human-readable tab label, e.g. 'Registration Form'")
    work_type = serializers.CharField(help_text="Machine key for specific pending work, e.g. 'unconverted_application'")
    work_type_label = serializers.CharField(help_text="Human-readable label for work type, e.g. 'Unconverted Application'")
    title = serializers.CharField(help_text="Short descriptive title of the pending task")
    description = serializers.CharField(help_text="Detailed explanation of what action is pending and why")
    urgency = serializers.ChoiceField(choices=['high', 'medium', 'low'], default='medium')
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    due_date = serializers.DateField(allow_null=True, required=False)
    action_url = serializers.CharField(allow_null=True, required=False, help_text="Recommended frontend or API route to resolve the task")
    meta = serializers.DictField(allow_null=True, required=False, help_text="Extra structured details (names, phone, course, amounts)")


class PendingTabCategorySerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class PendingTabSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    categories = PendingTabCategorySerializer(many=True, required=False)


class AcademicPendingDashboardSerializer(serializers.Serializer):
    """
    Top-level response serializer for Academic Pending Works Dashboard.
    """
    module = serializers.CharField(default="academic")
    module_label = serializers.CharField(default="Academy")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = PendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = PendingWorkItemSerializer(many=True)

