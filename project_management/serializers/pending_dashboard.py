from rest_framework import serializers


class PendingWorkItemSerializer(serializers.Serializer):
    """
    Standard cross-module schema for a single actionable pending work item.
    Follows the unified cross-module standard established in Academic and Leads.
    """
    id = serializers.CharField(help_text="Unique composite ID for frontend key rendering, e.g. 'proj_tasks_12'")
    record_id = serializers.IntegerField(allow_null=True, required=False, help_text="Database PK of the underlying record")
    tab = serializers.CharField(help_text="Submodule tab key")
    tab_label = serializers.CharField(help_text="Human-readable tab label")
    work_type = serializers.CharField(help_text="Machine key for specific pending work")
    work_type_label = serializers.CharField(help_text="Human-readable label for work type")
    title = serializers.CharField(help_text="Short descriptive title of the pending task")
    description = serializers.CharField(help_text="Detailed explanation of what action is pending and why")
    urgency = serializers.ChoiceField(choices=['high', 'medium', 'low'], default='medium')
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    due_date = serializers.DateField(allow_null=True, required=False)
    action_url = serializers.CharField(allow_null=True, required=False, help_text="Recommended frontend or API route")
    meta = serializers.DictField(allow_null=True, required=False, help_text="Extra structured details")


class PendingTabCategorySerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class PendingTabSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    categories = PendingTabCategorySerializer(many=True, required=False)


# =============================================================================
# 1. Project Management Pending Dashboard Serializer
# =============================================================================
class ProjectManagementPendingDashboardSerializer(serializers.Serializer):
    module = serializers.CharField(default="project_management")
    module_label = serializers.CharField(default="Project Management")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = PendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = PendingWorkItemSerializer(many=True)


# =============================================================================
# 2. Digital Marketing Pending Dashboard Serializer
# =============================================================================
class DigitalMarketingPendingDashboardSerializer(serializers.Serializer):
    module = serializers.CharField(default="digital_marketing")
    module_label = serializers.CharField(default="Digital Marketing")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = PendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = PendingWorkItemSerializer(many=True)


# =============================================================================
# 3. Testing Management Pending Dashboard Serializer
# =============================================================================
class TestingManagementPendingDashboardSerializer(serializers.Serializer):
    module = serializers.CharField(default="testing_management")
    module_label = serializers.CharField(default="Testing Management")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = PendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = PendingWorkItemSerializer(many=True)
