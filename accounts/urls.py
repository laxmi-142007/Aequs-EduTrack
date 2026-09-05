"""
URL configuration for the accounts app (RBAC portal routes).
"""
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Dashboard routing
    path("portal/redirect/", views.dashboard_redirect, name="dashboard_redirect"),

    # Admin portal
    path("portal/admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Employee portal
    path("portal/app/dashboard/", views.employee_dashboard, name="employee_dashboard"),

    # User management (admin only)
    path("portal/admin/users/", views.user_list, name="user_list"),
    path("portal/admin/users/create/", views.user_create, name="user_create"),
    path("portal/admin/roles/create/", views.role_create, name="role_create"),
    path("portal/admin/users/export/", views.user_export_csv, name="user_export_csv"),
    path("portal/admin/users/<int:pk>/detail/", views.user_detail_api, name="user_detail_api"),
    path("portal/admin/users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path(
        "portal/admin/users/<int:pk>/toggle/",
        views.user_toggle_active,
        name="user_toggle_active",
    ),
    path(
        "portal/admin/users/<int:pk>/reset-password/",
        views.user_reset_password,
        name="user_reset_password",
    ),

    # Password change on first login
    path(
        "portal/change-password/",
        views.force_password_change,
        name="force_password_change",
    ),
]
