# permissions.py
from rest_framework.permissions import BasePermission
from accounts.models import ModulePermission


# PARENT_MODULE_MAP = {
#     "sales": [
#         "quotation",
#         "sales_order",
#         "delivery",
#         "invoice",
#         "receipt",
#         "sales_returns",
#         "client",
#         "sales_person",
#         "reports"
#     ],
#     "purchase": [
#         "purchase",
#         "supplier",
#         "material_receive",
#         "reports"
#     ],
#     "finance": [
#         "accounts",
#         "receipt",
#         "reports"
#     ],
#     "crm": [
#         "leads",
#         "leads_management",
#         "project_management",
#         "marketing",
#         "reports"
#     ],
#     "hr": [
#         "hr_section",
#         "certificate",
#         "instructor",
#         "intern"
#     ],
# }


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

        # Superusers (admin) always have access
        if request.user.is_superuser:
            return True

        # For others, check required_module
        required_module = getattr(view, 'required_module', None)
        if not required_module:
            return True  # No specific module required

        return ModulePermission.objects.filter(user=request.user, module_name=required_module).exists()