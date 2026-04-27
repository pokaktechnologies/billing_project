# permissions.py
from rest_framework.permissions import BasePermission
from accounts.models import ModulePermission


PARENT_MODULE_MAP = [

    {
        "name": "dashboard",
        "submodules": [
            "hr_dashboard",
            "intern_dashboard",
            "bde_dashboard",
            "project_manager_dashboard",
            "developer_dashboard"
        ]
    },

    {
        "name": "home",
        "submodules": [
            "home"
        ]
    },

    {
        "name": "sales",
        "submodules": [
            "quotation",
            "invoice",
            "receipt",
            "sales_returns",
            "sales_reports"
        ]
    },

    {
        "name": "purchases",
        "submodules": [
            "purchase_order",
            "material_receive",
            "supplier",
            "purchase_reports"
        ]
    },

    {
        "name": "marketing",
        "submodules": [
            "marketing_data",
            "marketing_leads",
            "marketing_report"
        ]
    },

    {
        "name": "leads_management",
        "submodules": [
            "leads_management",
            "crm_reports"
        ]
    },

    {
        "name": "hr_controls",
        "submodules": [
            "hr_enquiries",
            "hr_staff_management",
            "hr_attendance",
            "hr_holidays",
            "hr_leaves",
            "hr_payroll",
            "hr_salary_statements",
            "hr_reports"
        ]
    },

    {
        "name": "Academy",
        "submodules": [
            "dashboard",
            "courses",
            "academy_interns",
            "faculty",
            "academy_payments",
            "centers",
            "classes",
            "form_submissions",
            "internship_reports"
        ]
    },

    {
        "name": "Faculty Management",
        "submodules": [
            "all_tasks",
            "my_courses",
            "faculty_interns",
            "submissions"
        ]
    },

    {
        "name": "Internship Pro",
        "submodules": [
            "my_tasks",
            "study_materials",
            "intern_payments"
        ]
    },
    
    {
        "name": "accounts",
        "submodules": [
            "journal_entries",
            "journal_voucher",
            "chart_of_accounts",
            "tax_settings",
            "finance_reports",
            "transactions"
        ]
    },

    {
        "name": "project_management",
        "submodules": [
            "project",
            "project_timeline",
            "project_reports"
        ]
    },

    {
        "name": "certificate",
        "submodules": [
            "certificate"
        ]
    },

    {
        "name": "products",
        "submodules": [
            "products",
            "stock",
            "inventory_reports"
        ]
    },

    {
        "name": "sales_person",
        "submodules": [
            "sales_person"
        ]
    },

    {
        "name": "client",
        "submodules": [
            "client"
        ]
    },

    {
        "name": "reports",
        "submodules": [
            "sales_reports",
            "purchase_reports",
            "finance_reports",
            "crm_reports",
            "hr_reports",
            "internship_reports",
            "project_reports",
            "inventory_reports"
        ]
    },

    {
        "name": "setup",
        "submodules": [
            "setup"
        ]
    },

]



# class HasModulePermission(BasePermission):
#
#     def has_permission(self, request, view):
#         # Admin bypass
#         if request.user.is_superuser:
#             return True
#         required_module = getattr(view, "required_module", None)
#
#         # If view does not require specific module
#         if not required_module:
#             return True
#
#         # Get all parent modules assigned to user
#         user_parents = set(
#             ModulePermission.objects.filter(
#                 user=request.user
#             ).values_list("module_name", flat=True)
#         )
#
#         # Check if required module belongs to any parent user has
#         for parent in user_parents:
#             children = PARENT_MODULE_MAP.get(parent, [])
#             if required_module in children:
#                 return True
#
#         return False


class HasModulePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers (admin) always have access
        if request.user.is_superuser:
            return True

        # For others, check required_module
        required_module = getattr(view, 'required_module', None)
        if not required_module:
            return True  # No specific module required

        return ModulePermission.objects.filter(user=request.user, module_name=required_module).exists()