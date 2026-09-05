from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom User Admin with role field."""
    list_display = UserAdmin.list_display + ("role", "is_active", "must_change_password")
    list_filter = UserAdmin.list_filter + ("role", "must_change_password")
    fieldsets = UserAdmin.fieldsets + (
        ("Role & Status", {"fields": ("role", "phone", "profile_photo", "must_change_password")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role & Status", {"fields": ("role", "phone", "must_change_password")}),
    )
