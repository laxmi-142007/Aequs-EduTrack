"""
Custom decorators for role-based access control.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def admin_required(view_func):
    """
    Decorator for function-based views.
    Restricts access to admin users (ADMIN, SUPER_ADMIN, or superuser).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_admin:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def employee_required(view_func):
    """
    Decorator for function-based views.
    Restricts access to any authenticated employee (non-anonymous).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


def has_module_permission(permission_name):
    """
    Decorator factory for function-based views.
    Checks if user has a specific permission or is an admin.
    Usage: @has_module_permission('inventory.view_laptop')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.has_perm(permission_name) or request.user.is_admin:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return decorator


def super_admin_required(view_func):
    """
    Decorator for function-based views.
    Restricts access to super admin / superuser only.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
