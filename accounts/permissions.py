# permissions.py
from rest_framework.permissions import BasePermission
from accounts.models import ModulePermission



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

