"""
Custom mixins for class-based views to enforce role-based access control.
"""
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class AdminRequiredMixin:
    """
    Mixin for class-based views.
    Restricts access to admin users (ADMIN, SUPER_ADMIN, or superuser).
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class EmployeeRequiredMixin:
    """
    Mixin for class-based views.
    Restricts access to any authenticated employee.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin:
    """
    Mixin for class-based views.
    Restricts access to super admin / superuser only.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ModulePermissionMixin:
    """
    Mixin for class-based views.
    Checks if user has a specific permission or is an admin.

    Set `required_permission` attribute on the view class.
    Example:
        class MyView(ModulePermissionMixin, View):
            required_permission = 'inventory.view_laptop'
    """
    required_permission = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if self.required_permission:
            if request.user.has_perm(self.required_permission) or request.user.is_admin:
                return super().dispatch(request, *args, **kwargs)
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
