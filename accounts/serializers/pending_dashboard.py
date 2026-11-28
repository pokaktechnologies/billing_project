from rest_framework import serializers


class PendingWorkItemSerializer(serializers.Serializer):
    """
    Standard schema for a single actionable pending work item.
    Matches AcademicPendingDashboard's item schema for cross-module unification.
    """
    id = serializers.CharField(help_text="Unique composite ID for frontend key rendering, e.g. 'quot_draft_12'")
    record_id = serializers.IntegerField(allow_null=True, required=False, help_text="Database PK of the underlying record")
    tab = serializers.CharField(help_text="Submodule tab key, e.g. 'quotation', 'invoice', 'purchase_order'")
    tab_label = serializers.CharField(help_text="Human-readable tab label, e.g. 'Quotations'")
    work_type = serializers.CharField(help_text="Machine key for specific pending work, e.g. 'quotation_draft'")
    work_type_label = serializers.CharField(help_text="Human-readable label for work type, e.g. 'Draft Quotation'")
    title = serializers.CharField(help_text="Short descriptive title of the pending task")
    description = serializers.CharField(help_text="Detailed explanation of what action is pending and why")
    urgency = serializers.ChoiceField(choices=["high", "medium", "low"], default="medium")
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    due_date = serializers.DateField(allow_null=True, required=False)
    action_url = serializers.CharField(allow_null=True, required=False, help_text="Recommended frontend or API route to resolve the task")
    meta = serializers.DictField(allow_null=True, required=False, help_text="Extra structured details (client/supplier, numbers, amounts)")


class PendingTabCategorySerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class PendingTabSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    categories = PendingTabCategorySerializer(many=True, required=False)


class SalesPendingWorkItemSerializer(PendingWorkItemSerializer):
    pass


class SalesPendingTabCategorySerializer(PendingTabCategorySerializer):
    pass


class SalesPendingTabSerializer(PendingTabSerializer):
    pass


class SalesPendingDashboardSerializer(serializers.Serializer):
    """
    Top-level response serializer for Sales Pending Works Dashboard.
    """
    module = serializers.CharField(default="sales")
    module_label = serializers.CharField(default="Sales")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = SalesPendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = SalesPendingWorkItemSerializer(many=True)


class PurchasePendingWorkItemSerializer(PendingWorkItemSerializer):
    pass


class PurchasePendingTabCategorySerializer(PendingTabCategorySerializer):
    pass


class PurchasePendingTabSerializer(PendingTabSerializer):
    pass


class PurchasePendingDashboardSerializer(serializers.Serializer):
    """
    Top-level response serializer for Purchases Pending Works Dashboard.
    """
    module = serializers.CharField(default="purchases")
    module_label = serializers.CharField(default="Purchases")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = PurchasePendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = PurchasePendingWorkItemSerializer(many=True)


class ProductsPendingWorkItemSerializer(PendingWorkItemSerializer):
    pass


class ProductsPendingTabCategorySerializer(PendingTabCategorySerializer):
    pass


class ProductsPendingTabSerializer(PendingTabSerializer):
    pass


class ProductsPendingDashboardSerializer(serializers.Serializer):
    """
    Top-level response serializer for Products Pending Works Dashboard.
    """
    module = serializers.CharField(default="products")
    module_label = serializers.CharField(default="Products")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = ProductsPendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = ProductsPendingWorkItemSerializer(many=True)
