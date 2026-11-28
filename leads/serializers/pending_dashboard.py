from rest_framework import serializers


class MarketingPendingWorkItemSerializer(serializers.Serializer):
    """
    Standard schema for a single actionable pending marketing work item.
    Follows the identical unified contract established in the Academic pending dashboard.
    """
    id = serializers.CharField(help_text="Unique composite ID for frontend key rendering, e.g. 'mkt_fu_102'")
    record_id = serializers.IntegerField(allow_null=True, required=False, help_text="Database PK of the underlying record")
    tab = serializers.CharField(help_text="Submodule tab key, e.g. 'daily_activity', 'leads', 'follow_ups', 'meetings', 'reminders', 'communication', 'marketing_data'")
    tab_label = serializers.CharField(help_text="Human-readable tab label, e.g. 'Daily Activity'")
    work_type = serializers.CharField(help_text="Machine key for specific pending work, e.g. 'overdue_followup'")
    work_type_label = serializers.CharField(help_text="Human-readable label for work type, e.g. 'Overdue Follow-up'")
    title = serializers.CharField(help_text="Short descriptive title of the pending task")
    description = serializers.CharField(help_text="Detailed explanation of what action is pending and why")
    urgency = serializers.ChoiceField(choices=['high', 'medium', 'low'], default='medium')
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    due_date = serializers.DateField(allow_null=True, required=False)
    action_url = serializers.CharField(allow_null=True, required=False, help_text="Recommended frontend or API route to resolve the task")
    meta = serializers.DictField(allow_null=True, required=False, help_text="Extra structured details (lead name, phone, course, meeting place, etc.)")


class MarketingPendingTabCategorySerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class MarketingPendingTabSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    categories = MarketingPendingTabCategorySerializer(many=True, required=False)


class MarketingPendingDashboardSerializer(serializers.Serializer):
    """
    Top-level response serializer for Marketing Module Pending Works Dashboard.
    Follows the cross-module unified standard contract.
    """
    module = serializers.CharField(default="marketing")
    module_label = serializers.CharField(default="Marketing")
    salesperson_info = serializers.DictField(allow_null=True, required=False, help_text="Current staff/salesperson scope info")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = MarketingPendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = MarketingPendingWorkItemSerializer(many=True)


class LeadManagementPendingDashboardSerializer(serializers.Serializer):
    """
    Top-level response serializer for Lead Management Pending Works Dashboard.
    Follows the cross-module unified standard contract.
    """
    module = serializers.CharField(default="lead_management")
    module_label = serializers.CharField(default="Lead Management")
    salesperson_info = serializers.DictField(allow_null=True, required=False, help_text="Filter/scope info if filtered by salesperson")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = MarketingPendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = MarketingPendingWorkItemSerializer(many=True)
